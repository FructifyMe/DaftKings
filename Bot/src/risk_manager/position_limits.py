"""Position limits to prevent correlated and over-concentrated betting."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from config import CONFIG
from src.models import BettingOpportunity

logger = logging.getLogger(__name__)

BOT_ROOT = Path(__file__).resolve().parent.parent.parent
BETS_LOG = BOT_ROOT / "data" / "logs" / "bets_log.csv"


class PositionLimits:
    """Enforces position limits to manage concentration risk."""

    MAX_BETS_PER_GAME = 1
    MAX_BETS_PER_SPORT = 2
    GOLF_OUTRIGHT_MAX_PCT = 0.02  # 2% cap on golf outright winner bets

    def check(
        self, opportunity: BettingOpportunity, stake_usd: float = 0.0
    ) -> tuple[bool, str]:
        """Check if a new bet is allowed given today's existing positions.

        Returns (approved: bool, reason: str).
        """
        today_bets = self._get_todays_bets()

        # Block: more than 1 bet on same game
        game_bets = today_bets[
            (today_bets["event_id"] == opportunity.event_id)
        ] if not today_bets.empty and "event_id" in today_bets.columns else pd.DataFrame()
        if len(game_bets) >= self.MAX_BETS_PER_GAME:
            reason = f"Already have {len(game_bets)} bet(s) on this game today"
            logger.warning("Position limit blocked: %s", reason)
            return False, reason

        # Block: correlated bets (same team ML + spread same day)
        if not today_bets.empty and "home_team" in today_bets.columns:
            teams = {opportunity.home_team, opportunity.away_team}
            for _, row in today_bets.iterrows():
                existing_teams = {row.get("home_team", ""), row.get("away_team", "")}
                if teams & existing_teams:
                    existing_market = row.get("market_type", "")
                    new_market = opportunity.market_type
                    # Block if one is h2h and other is spreads (correlated)
                    correlated_pair = {"h2h", "spreads"}
                    if {existing_market, new_market} == correlated_pair:
                        reason = (
                            f"Correlated bet blocked: already have {existing_market} bet "
                            f"on same teams, cannot add {new_market}"
                        )
                        logger.warning("Position limit blocked: %s", reason)
                        return False, reason

        # Block: more than 2 bets on same sport in one day
        if not today_bets.empty and "sport" in today_bets.columns:
            sport_bets = today_bets[today_bets["sport"] == opportunity.sport]
            if len(sport_bets) >= self.MAX_BETS_PER_SPORT:
                reason = f"Already have {len(sport_bets)} bets on {opportunity.sport} today (max {self.MAX_BETS_PER_SPORT})"
                logger.warning("Position limit blocked: %s", reason)
                return False, reason

        # Block: golf outright winner bet > 2% of bankroll
        if opportunity.sport == "golf_pga" and opportunity.market_type == "outrights":
            max_golf_stake = CONFIG.starting_bankroll * self.GOLF_OUTRIGHT_MAX_PCT
            if stake_usd > max_golf_stake:
                reason = (
                    f"Golf outright stake ${stake_usd:.2f} exceeds "
                    f"${max_golf_stake:.2f} cap (2% of bankroll)"
                )
                logger.warning("Position limit blocked: %s", reason)
                return False, reason

        return True, "Approved"

    def _get_todays_bets(self) -> pd.DataFrame:
        """Read today's bets from the log."""
        if not BETS_LOG.exists():
            return pd.DataFrame()

        try:
            df = pd.read_csv(BETS_LOG)
            if df.empty or "timestamp" not in df.columns:
                return pd.DataFrame()

            today = datetime.now().strftime("%Y-%m-%d")
            return df[df["timestamp"].str.startswith(today)]
        except Exception as e:
            logger.warning("Error reading bets log for position check: %s", e)
            return pd.DataFrame()
