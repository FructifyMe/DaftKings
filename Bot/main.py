"""DaftKings Bot orchestrator. Runs the full scan -> analyze -> risk -> execute cycle."""

from __future__ import annotations

import logging
import sys
import time

from config import CONFIG
from src.alerting.telegram_bot import TelegramBot
from src.analyzer.claude_analyzer import AnalysisError, ClaudeAnalyzer
from src.executor.settlement import SettlementProcessor
from src.analyzer.situational import SituationalAnalyzer
from src.analyzer.value_detector import ValueDetector
from src.executor.bet_logger import BetLogger
from src.executor.kalshi_executor import KalshiExecutor
from src.models import BetOrder, BettingOpportunity
from src.risk_manager.kelly import KellyCalculator
from src.risk_manager.kill_switch import KillSwitch
from src.risk_manager.position_limits import PositionLimits
from src.scanner.arb_detector import ArbDetector
from src.scanner.odds_fetcher import OddsFetcher

logger = logging.getLogger(__name__)


def run_cycle() -> None:
    """Main bot cycle. Called by scripts/run_bot.py every 10 minutes."""
    start_time = time.time()
    bet_logger = BetLogger()
    telegram = TelegramBot()
    errors = 0
    bets_placed = 0
    markets_scanned = 0
    arbs_found = 0
    opportunities_analyzed = 0

    logger.info("=" * 60)
    logger.info("DaftKings Bot cycle starting | run_id=%s | paper_mode=%s",
                bet_logger.run_id, CONFIG.paper_mode)
    logger.info("=" * 60)

    try:
        # 1. Check kill switch — if active, skip entire cycle
        kill_switch = KillSwitch()
        if kill_switch.is_active():
            stats = kill_switch.get_daily_stats()
            logger.info("Kill switch active — skipping cycle. Stats: %s", stats)
            bet_logger.log_run(0, 0, 0, 0, time.time() - start_time)
            return

        # 2. Initialize modules
        odds_fetcher = OddsFetcher()
        arb_detector = ArbDetector()
        situational = SituationalAnalyzer()
        value_detector = ValueDetector()
        claude_analyzer = ClaudeAnalyzer()
        kelly = KellyCalculator()
        position_limits = PositionLimits()
        executor = KalshiExecutor()

        # 3. Fetch all odds
        logger.info("Scanning all sports for odds...")
        all_markets = odds_fetcher.get_all_sports()
        markets_scanned = len(all_markets)
        logger.info("Scanned %d total markets", markets_scanned)

        if not all_markets:
            logger.info("No markets found — exiting cycle")
            bet_logger.log_run(0, 0, 0, 0, time.time() - start_time)
            return

        # 4. Run arb detection on all markets
        arb_results = arb_detector.detect_all(all_markets)
        arbs_found = len(arb_results)
        for arb in arb_results:
            bet_logger.log_arb(arb)
            telegram.send_arb_alert(arb)

        # 5. Build BettingOpportunity objects and enrich with arb flags
        arb_event_map = {a.event_id: a for a in arb_results}
        opportunities: list[BettingOpportunity] = []
        for market in all_markets:
            arb = arb_event_map.get(market.event_id)
            opp = BettingOpportunity.from_market_odds(
                market,
                arb_flag=arb is not None,
                arb_result=arb,
            )
            opportunities.append(opp)

        # 6. Pre-filter with ValueDetector
        filtered = [opp for opp in opportunities if value_detector.pre_filter(opp)]
        logger.info("Pre-filter: %d/%d opportunities passed", len(filtered), len(opportunities))

        # 7. Enrich with situational factors and sort by preliminary edge
        factors_map: dict[str, dict] = {}
        for opp in filtered:
            factors = situational.enrich(opp)
            factors_map[opp.event_id] = factors
            opp.situational_factors = factors

        sorted_opps = value_detector.sort_by_edge(filtered, factors_map)

        # 7b. Ensure sport diversity: pick top opportunities per sport, then interleave
        # This prevents one sport (e.g. soccer arbs) from consuming all Haiku calls
        by_sport: dict[str, list] = {}
        for opp in sorted_opps:
            by_sport.setdefault(opp.sport, []).append(opp)

        diverse_opps: list = []
        max_per_sport = max(3, CONFIG.max_daily_bets // max(len(by_sport), 1))
        # Round-robin across sports
        sport_iters = {s: iter(opps) for s, opps in by_sport.items()}
        while sport_iters and len(diverse_opps) < len(sorted_opps):
            exhausted = []
            for sport, it in sport_iters.items():
                count_for_sport = sum(1 for o in diverse_opps if o.sport == sport)
                if count_for_sport >= max_per_sport:
                    exhausted.append(sport)
                    continue
                try:
                    diverse_opps.append(next(it))
                except StopIteration:
                    exhausted.append(sport)
            for s in exhausted:
                sport_iters.pop(s, None)

        logger.info(
            "Sport diversity: %s",
            {s: sum(1 for o in diverse_opps if o.sport == s) for s in by_sport},
        )
        sorted_opps = diverse_opps

        # 8. Analyze each opportunity with Haiku
        for opp in sorted_opps:
            # Re-check kill switch before each bet attempt
            if kill_switch.is_active():
                logger.info("Kill switch triggered mid-cycle — stopping")
                stats = kill_switch.get_daily_stats()
                telegram.send_kill_switch_alert(stats)
                break

            opportunities_analyzed += 1
            try:
                analysis = claude_analyzer.analyze(opp, opp.situational_factors)
            except AnalysisError as e:
                logger.error("Haiku analysis failed for %s: %s", opp.event_id, e)
                errors += 1
                continue

            # Log all decisions (bet AND pass)
            if analysis.recommendation == "pass":
                bet_logger.log_pass(opp, analysis)
                logger.info("PASS: %s | %s @ %s | %s",
                            opp.sport, opp.away_team, opp.home_team, analysis.reasoning)
                continue

            # Recommendation is "bet" — apply thresholds
            min_confidence = 0.50 if CONFIG.paper_mode else 0.70
            if analysis.confidence < min_confidence or analysis.estimated_edge < CONFIG.min_edge_threshold:
                logger.info(
                    "Below threshold: conf=%.2f (need 0.70), edge=%.2f%% (need %.0f%%)",
                    analysis.confidence, analysis.estimated_edge * 100,
                    CONFIG.min_edge_threshold * 100,
                )
                bet_logger.log_pass(opp, analysis)
                continue

            # Risk checks
            stake = kelly.calculate_stake(
                CONFIG.starting_bankroll,
                analysis.estimated_edge,
                CONFIG.kelly_fraction,
                CONFIG.max_bet_pct,
            )

            if stake <= 0:
                logger.info("Kelly returned $0 stake — skipping")
                bet_logger.log_pass(opp, analysis)
                continue

            approved, reason = position_limits.check(opp, stake)
            if not approved:
                logger.info("Position limits blocked: %s", reason)
                bet_logger.log_pass(opp, analysis)
                continue

            # Execute bet
            bet_order = BetOrder(
                opportunity=opp,
                analysis=analysis,
                stake_usd=stake,
                paper_mode=CONFIG.paper_mode,
            )
            bet_result = executor.place_bet(bet_order)
            bet_logger.log(bet_result)
            telegram.send_bet_alert(bet_result)
            bets_placed += 1

            logger.info(
                "BET PLACED [%s]: %s | %s @ %s | %s=%s | $%.2f | edge=%.1f%%",
                bet_result.status, opp.sport, opp.away_team, opp.home_team,
                analysis.side, opp.best_odds.get(analysis.side, "?"),
                stake, analysis.estimated_edge * 100,
            )

            # Check if max daily bets reached
            if bets_placed >= CONFIG.max_daily_bets:
                logger.info("Max daily bets reached (%d) — stopping", CONFIG.max_daily_bets)
                break

    except Exception as e:
        logger.exception("Unhandled error in bot cycle: %s", e)
        errors += 1
        telegram.send_error(f"Bot cycle failed: {e}")

    # Log run summary (include token costs if analyzer was initialized)
    duration = time.time() - start_time
    haiku_calls = claude_analyzer.call_count if 'claude_analyzer' in locals() else 0
    input_tokens = claude_analyzer.total_input_tokens if 'claude_analyzer' in locals() else 0
    output_tokens = claude_analyzer.total_output_tokens if 'claude_analyzer' in locals() else 0
    api_cost = claude_analyzer.total_cost_usd if 'claude_analyzer' in locals() else 0.0
    bet_logger.log_run(
        markets_scanned, arbs_found, opportunities_analyzed, bets_placed,
        duration, errors, haiku_calls, input_tokens, output_tokens, api_cost,
    )

    logger.info(
        "Cycle complete: %d markets, %d arbs, %d analyzed, %d bets, %.1fs, %d errors",
        markets_scanned, arbs_found, opportunities_analyzed, bets_placed, duration, errors,
    )

    # 9. Settle any completed bets from previous cycles
    try:
        settled = run_settlement(telegram)
        if settled:
            logger.info("Settled %d bets this cycle", len(settled))
    except Exception as e:
        logger.error("Settlement failed: %s", e)

    if errors > 0:
        sys.exit(1)


def run_settlement(telegram: TelegramBot | None = None) -> list:
    """Settle completed bets. Can be called standalone or as part of run_cycle."""
    telegram = telegram or TelegramBot()
    settler = SettlementProcessor()

    logger.info("Running bet settlement...")
    results = settler.settle_bets()

    if results:
        telegram.send_settlement_summary(results)
        for r in results:
            logger.info(
                "SETTLED: %s | %s vs %s | %s | %s | P&L $%+.2f",
                r.sport, r.home_team, r.away_team, r.market_type,
                r.result.upper(), r.pnl_usd,
            )
    else:
        logger.info("No bets settled this cycle")

    return results
