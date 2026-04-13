"""CSV logging for all bet decisions — placed, passed, and arb detections."""

from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.models import AnalysisResult, ArbResult, BetResult, BettingOpportunity

logger = logging.getLogger(__name__)

BOT_ROOT = Path(__file__).resolve().parent.parent.parent
BETS_LOG = BOT_ROOT / "data" / "logs" / "bets_log.csv"
ARB_LOG = BOT_ROOT / "data" / "logs" / "arb_log.csv"
RUN_LOG = BOT_ROOT / "data" / "logs" / "run_log.csv"

BETS_COLUMNS = [
    "timestamp", "run_id", "sport", "league", "event_id", "home_team", "away_team",
    "game_time", "market_type", "recommended_side", "bet_description", "bet_odds",
    "bet_book", "best_odds", "implied_prob",
    "estimated_true_prob", "estimated_edge", "confidence", "kelly_stake_pct",
    "actual_stake_usd", "paper_mode", "kalshi_order_id", "result", "pnl_usd",
    "closing_odds", "clv_points", "haiku_reasoning", "key_factors",
    "arb_flag", "arb_books", "score_summary",
]

ARB_COLUMNS = [
    "timestamp", "sport", "event_id", "home_team", "away_team", "market_type",
    "mispriced_side", "better_book", "worse_book", "better_odds", "implied_total",
    "arb_profit_pct", "value_recommendation",
]

RUN_COLUMNS = [
    "timestamp", "run_id", "markets_scanned", "arbs_found", "opportunities_analyzed",
    "bets_placed", "duration_seconds", "errors", "haiku_calls", "input_tokens",
    "output_tokens", "api_cost_usd",
]


class BetLogger:
    """Logs all bet decisions to CSV files."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self._ensure_files()

    def log(self, bet_result: BetResult) -> None:
        """Log a placed bet (paper or live) to bets_log.csv."""
        opp = bet_result.bet_order.opportunity
        analysis = bet_result.bet_order.analysis
        side = analysis.side or ""
        best_odds_for_side = opp.best_odds.get(side, opp.best_odds.get(opp.home_team, ""))
        implied_for_side = opp.implied_probs.get(side, 0.0)

        row = {
            "timestamp": bet_result.timestamp.isoformat(),
            "run_id": self.run_id,
            "sport": opp.sport,
            "league": opp.league,
            "event_id": opp.event_id,
            "home_team": opp.home_team,
            "away_team": opp.away_team,
            "game_time": opp.game_time.isoformat(),
            "market_type": opp.market_type,
            "recommended_side": side,
            "bet_description": analysis.bet_description or "",
            "bet_odds": analysis.bet_odds or "",
            "bet_book": analysis.bet_book or "",
            "best_odds": best_odds_for_side,
            "implied_prob": f"{implied_for_side:.4f}",
            "estimated_true_prob": f"{analysis.estimated_true_probability:.4f}",
            "estimated_edge": f"{analysis.estimated_edge:.4f}",
            "confidence": f"{analysis.confidence:.4f}",
            "kelly_stake_pct": f"{bet_result.bet_order.stake_usd / 1000:.4f}",
            "actual_stake_usd": f"{bet_result.bet_order.stake_usd:.2f}",
            "paper_mode": bet_result.bet_order.paper_mode,
            "kalshi_order_id": bet_result.kalshi_order_id or "",
            "result": "",  # Filled later on game completion
            "pnl_usd": "",
            "closing_odds": "",
            "clv_points": "",
            "haiku_reasoning": analysis.reasoning,
            "key_factors": " | ".join(analysis.key_factors) if analysis.key_factors else "",
            "arb_flag": opp.arb_flag,
            "arb_books": opp.arb_result.better_book if opp.arb_result else "",
            "score_summary": "",
        }
        self._append_row(BETS_LOG, BETS_COLUMNS, row)
        logger.info("Logged bet: %s %s %s $%.2f", opp.sport, side, opp.event_id, bet_result.bet_order.stake_usd)

    def log_pass(self, opportunity: BettingOpportunity, analysis: AnalysisResult) -> None:
        """Log a skipped/passed bet with reasoning."""
        row = {
            "timestamp": datetime.now().isoformat(),
            "run_id": self.run_id,
            "sport": opportunity.sport,
            "league": opportunity.league,
            "event_id": opportunity.event_id,
            "home_team": opportunity.home_team,
            "away_team": opportunity.away_team,
            "game_time": opportunity.game_time.isoformat(),
            "market_type": opportunity.market_type,
            "recommended_side": analysis.side or "none",
            "bet_description": analysis.bet_description or "",
            "bet_odds": analysis.bet_odds or "",
            "bet_book": analysis.bet_book or "",
            "best_odds": "",
            "implied_prob": "",
            "estimated_true_prob": f"{analysis.estimated_true_probability:.4f}",
            "estimated_edge": f"{analysis.estimated_edge:.4f}",
            "confidence": f"{analysis.confidence:.4f}",
            "kelly_stake_pct": "0",
            "actual_stake_usd": "0",
            "paper_mode": True,
            "kalshi_order_id": "",
            "result": "pass",
            "pnl_usd": "0",
            "closing_odds": "",
            "clv_points": "",
            "haiku_reasoning": f"PASS: {analysis.reasoning}",
            "key_factors": " | ".join(analysis.key_factors) if analysis.key_factors else "",
            "arb_flag": opportunity.arb_flag,
            "arb_books": "",
            "score_summary": "",
        }
        self._append_row(BETS_LOG, BETS_COLUMNS, row)

    def log_arb(self, arb_result: ArbResult) -> None:
        """Log an arbitrage detection to arb_log.csv."""
        row = {
            "timestamp": datetime.now().isoformat(),
            "sport": arb_result.sport,
            "event_id": arb_result.event_id,
            "home_team": arb_result.home_team,
            "away_team": arb_result.away_team,
            "market_type": arb_result.market_type,
            "mispriced_side": arb_result.mispriced_side,
            "better_book": arb_result.better_book,
            "worse_book": arb_result.worse_book,
            "better_odds": arb_result.better_odds,
            "implied_total": f"{arb_result.implied_total:.4f}",
            "arb_profit_pct": f"{arb_result.arb_profit_pct:.2f}",
            "value_recommendation": arb_result.value_recommendation,
        }
        self._append_row(ARB_LOG, ARB_COLUMNS, row)
        logger.info("Logged arb: %s %.1f%%", arb_result.event_id, arb_result.arb_profit_pct)

    def log_run(
        self,
        markets_scanned: int,
        arbs_found: int,
        opportunities_analyzed: int,
        bets_placed: int,
        duration_seconds: float,
        errors: int = 0,
        haiku_calls: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        api_cost_usd: float = 0.0,
    ) -> None:
        """Log run summary to run_log.csv."""
        row = {
            "timestamp": datetime.now().isoformat(),
            "run_id": self.run_id,
            "markets_scanned": markets_scanned,
            "arbs_found": arbs_found,
            "opportunities_analyzed": opportunities_analyzed,
            "bets_placed": bets_placed,
            "duration_seconds": f"{duration_seconds:.1f}",
            "errors": errors,
            "haiku_calls": haiku_calls,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "api_cost_usd": f"{api_cost_usd:.4f}",
        }
        self._append_row(RUN_LOG, RUN_COLUMNS, row)

    def get_todays_bets(self) -> pd.DataFrame:
        """Returns today's rows from bets_log.csv."""
        if not BETS_LOG.exists():
            return pd.DataFrame(columns=BETS_COLUMNS)

        try:
            df = pd.read_csv(BETS_LOG)
            if df.empty:
                return pd.DataFrame(columns=BETS_COLUMNS)
            today = datetime.now().strftime("%Y-%m-%d")
            return df[df["timestamp"].str.startswith(today)]
        except Exception as e:
            logger.warning("Error reading bets log: %s", e)
            return pd.DataFrame(columns=BETS_COLUMNS)

    def _append_row(self, filepath: Path, columns: list[str], row: dict) -> None:
        """Append a row to a CSV file. Creates file with headers if it doesn't exist."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        file_exists = filepath.exists()

        try:
            with open(filepath, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)
        except Exception as e:
            logger.error("Failed to write to %s: %s", filepath, e)

    def _ensure_files(self) -> None:
        """Create log directories if they don't exist."""
        for path in [BETS_LOG, ARB_LOG, RUN_LOG]:
            path.parent.mkdir(parents=True, exist_ok=True)
