"""Kelly Criterion stake sizing. Quarter-Kelly by default."""

from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)


class KellyCalculator:
    """Calculates bet stake using the Kelly Criterion."""

    def calculate_stake(
        self,
        bankroll: float,
        estimated_edge: float,
        kelly_fraction: float = 0.25,
        max_bet_pct: float = 0.05,
    ) -> float:
        """Calculate Quarter-Kelly stake.

        Formula: stake = bankroll * edge * kelly_fraction
        Hard cap: min(calculated_stake, bankroll * max_bet_pct)
        Rounds to nearest $0.50 for clean bet sizes.
        Returns 0 if edge <= 0 or bankroll <= 0.

        Example:
            bankroll=$1000, edge=0.07, fraction=0.25, max=5%
            stake = 1000 * 0.07 * 0.25 = $17.50
            cap = 1000 * 0.05 = $50.00
            result = $17.50
        """
        if estimated_edge <= 0 or bankroll <= 0:
            return 0.0

        raw_stake = bankroll * estimated_edge * kelly_fraction
        cap = bankroll * max_bet_pct
        stake = min(raw_stake, cap)

        # Round to nearest $0.50
        stake = round(stake * 2) / 2

        logger.info(
            "Kelly: bankroll=$%.2f, edge=%.2f%%, fraction=%.2f → raw=$%.2f, cap=$%.2f, final=$%.2f",
            bankroll, estimated_edge * 100, kelly_fraction, raw_stake, cap, stake,
        )

        return stake
