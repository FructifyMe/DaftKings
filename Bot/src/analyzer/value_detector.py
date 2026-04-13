"""Pre-filter that runs BEFORE calling Haiku to avoid wasting API calls."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from config import CONFIG
from src.models import BettingOpportunity

logger = logging.getLogger(__name__)

BOT_ROOT = Path(__file__).resolve().parent.parent.parent
BETS_LOG = BOT_ROOT / "data" / "logs" / "bets_log.csv"


class ValueDetector:
    """Filters and prioritizes betting opportunities before sending to Haiku."""

    def pre_filter(self, opportunity: BettingOpportunity) -> bool:
        """Returns True if the opportunity is worth sending to Haiku for analysis.

        Pre-filter criteria (ALL must be met):
        1. Best available odds exist for both sides
        2. sum(implied_probs) > 1.0 (not already arbed out — arbs handled separately)
        3. At least one side has implied prob between 25% and 75%
        4. Game is within next 24 hours (or PGA tournament)
        5. No existing position in this game in today's bets log
        """
        # 1. Must have odds on at least two sides
        if len(opportunity.best_odds) < 2:
            logger.debug("Filtered out %s: fewer than 2 sides with odds", opportunity.event_id)
            return False

        # 2. Implied probs must sum to > 1.0 (standard market, not already arbed out)
        total_implied = sum(opportunity.implied_probs.values())
        if total_implied <= 1.0:
            logger.debug("Filtered out %s: implied probs sum %.3f <= 1.0 (arb territory)",
                         opportunity.event_id, total_implied)
            return False

        # 3. At least one side between 25% and 75% (avoid extreme favorites/longshots)
        has_reasonable_side = any(
            0.25 <= prob <= 0.75
            for prob in opportunity.implied_probs.values()
        )
        if not has_reasonable_side:
            logger.debug("Filtered out %s: no side in 25-75%% range", opportunity.event_id)
            return False

        # 4. Game within 24 hours (PGA tournaments exempt — multi-day events)
        if opportunity.sport != "golf_pga":
            now = datetime.now(timezone.utc)
            cutoff = now + timedelta(hours=24)
            game_time = opportunity.game_time
            if game_time.tzinfo is None:
                game_time = game_time.replace(tzinfo=timezone.utc)
            if game_time > cutoff:
                logger.debug("Filtered out %s: game_time %s beyond 24h window",
                             opportunity.event_id, game_time)
                return False

        # 5. No existing position in this game today
        if self._has_existing_position(opportunity.event_id):
            logger.debug("Filtered out %s: already have position today", opportunity.event_id)
            return False

        return True

    def estimate_preliminary_edge(
        self, opportunity: BettingOpportunity, situational_factors: dict
    ) -> float:
        """Quick heuristic edge estimate BEFORE Haiku, used to prioritize opportunities.

        Balances multiple signals so all sports get fair representation,
        not just arb-flagged games.

        Returns estimated edge as 0.0-1.0.
        """
        edge = 0.0

        # Base: market inefficiency signal from vig spread across books
        probs = list(opportunity.implied_probs.values())
        if len(probs) >= 2:
            total_vig = sum(probs) - 1.0
            edge += min(total_vig * 0.5, 0.03)

        # Cross-book odds divergence: biggest gap between books on the same outcome
        # This catches value even when arb threshold isn't met
        if hasattr(opportunity, 'all_book_odds') and opportunity.all_book_odds:
            max_spread = 0
            for side, odds_list in opportunity.all_book_odds.items():
                if len(odds_list) >= 2:
                    spread = max(odds_list) - min(odds_list)
                    max_spread = max(max_spread, spread)
            if max_spread > 20:
                edge += 0.015  # Books disagree meaningfully
            if max_spread > 50:
                edge += 0.015  # Strong disagreement

        # Sport-specific base edge: some markets are less efficient
        sport_bonus = {
            "soccer_usa_mls": 0.015,   # MLS is less efficient
            "baseball_mlb": 0.01,      # Pitcher matchup edge
            "icehockey_nhl": 0.01,     # Road underdog value
        }
        edge += sport_bonus.get(opportunity.sport, 0.005)

        # Rest advantage bonus
        home_rest = situational_factors.get("home_rest_days")
        away_rest = situational_factors.get("away_rest_days")
        if home_rest is not None and away_rest is not None:
            rest_diff = abs(home_rest - away_rest)
            if rest_diff >= 2:
                edge += 0.02

        # Back-to-back opportunity
        if situational_factors.get("is_b2b"):
            edge += 0.015

        # Weather impact (NFL/MLB outdoor sports)
        weather = situational_factors.get("weather")
        if weather and isinstance(weather, dict):
            wind = weather.get("wind_mph", 0) or 0
            if wind > 15:
                edge += 0.01

        # Arb flag bonus — still valuable but not overwhelming
        if opportunity.arb_flag:
            edge += 0.02

        return round(edge, 4)

    def sort_by_edge(
        self,
        opportunities: list[BettingOpportunity],
        situational_factors_map: dict[str, dict],
    ) -> list[BettingOpportunity]:
        """Sort opportunities by preliminary edge descending."""
        for opp in opportunities:
            factors = situational_factors_map.get(opp.event_id, {})
            opp.preliminary_edge = self.estimate_preliminary_edge(opp, factors)

        return sorted(opportunities, key=lambda o: o.preliminary_edge, reverse=True)

    def _has_existing_position(self, event_id: str) -> bool:
        """Check if we already have a bet on this event today."""
        if not BETS_LOG.exists():
            return False

        try:
            df = pd.read_csv(BETS_LOG)
            if df.empty or "event_id" not in df.columns or "timestamp" not in df.columns:
                return False

            today = datetime.now().strftime("%Y-%m-%d")
            today_bets = df[df["timestamp"].str.startswith(today)]
            return event_id in today_bets["event_id"].values
        except Exception as e:
            logger.warning("Error reading bets log for position check: %s", e)
            return False
