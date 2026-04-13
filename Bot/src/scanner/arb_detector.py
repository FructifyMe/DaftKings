"""Detects cross-book arbitrage opportunities and flags the mispriced side as a value signal."""

from __future__ import annotations

import logging

from src.models import ArbResult, MarketOdds
from src.scanner.odds_fetcher import OddsFetcher

logger = logging.getLogger(__name__)


class ArbDetector:
    """Scans markets for arbitrage where implied probabilities sum to < threshold."""

    ARB_THRESHOLD = 0.98  # Flag if implied probs sum to < 98%

    def detect(self, market: MarketOdds) -> ArbResult | None:
        """Returns ArbResult if arbitrage exists across bookmakers, else None.

        For two-way markets (h2h, spreads, totals), finds the best price on each
        side across all books. If the sum of implied probabilities from those best
        prices is below the threshold, an arb exists.
        """
        if len(market.best_odds) < 2:
            return None

        # For standard two-way markets, pick the two primary sides
        sides = list(market.best_odds.keys())
        if len(sides) < 2:
            return None

        # Use the first two sides (home/away for h2h, over/under for totals, etc.)
        side_a, side_b = sides[0], sides[1]

        prob_a = market.implied_probs.get(side_a, 0.0)
        prob_b = market.implied_probs.get(side_b, 0.0)

        if prob_a <= 0 or prob_b <= 0:
            return None

        implied_total = prob_a + prob_b

        if implied_total >= self.ARB_THRESHOLD:
            return None

        # Arb detected — identify which side is mispriced (has better value)
        mispriced_side, better_book, worse_book, better_odds = (
            self._identify_mispriced_side(market, side_a, side_b, prob_a, prob_b)
        )

        arb_profit_pct = (1 - implied_total) * 100

        result = ArbResult(
            event_id=market.event_id,
            sport=market.sport,
            home_team=market.home_team,
            away_team=market.away_team,
            market_type=market.market_type,
            mispriced_side=mispriced_side,
            better_book=better_book,
            worse_book=worse_book,
            better_odds=better_odds,
            implied_total=implied_total,
            arb_profit_pct=arb_profit_pct,
            value_recommendation=(
                f"Bet {mispriced_side} at {better_book} ({better_odds:+d}) as value — "
                f"do NOT bet both sides"
            ),
        )

        logger.info(
            "ARB DETECTED: %s @ %s | %s | %.1f%% margin | value: %s at %s",
            market.away_team, market.home_team, market.market_type,
            arb_profit_pct, mispriced_side, better_book,
        )

        return result

    def _identify_mispriced_side(
        self,
        market: MarketOdds,
        side_a: str,
        side_b: str,
        prob_a: float,
        prob_b: float,
    ) -> tuple[str, str, str, int]:
        """Identify which side + book has the mispriced (value) odds.

        The mispriced side is the one where the best available odds imply a LOWER
        probability than what's likely true — meaning the bookmaker is offering
        too generous a price. We pick the side with the lower implied prob
        relative to what should be a fair split, because that side is "too cheap."

        Returns: (mispriced_side, better_book, worse_book, better_odds)
        """
        # The side with lower implied prob from best odds is the "too cheap" one
        if prob_a <= prob_b:
            value_side = side_a
            other_side = side_b
        else:
            value_side = side_b
            other_side = side_a

        # Find which bookmaker offers the best price on the value side
        best_price = market.best_odds[value_side]
        better_book = ""
        for book, outcomes in market.bookmaker_odds.items():
            if value_side in outcomes and outcomes[value_side] == best_price:
                better_book = book
                break

        # Find a representative book on the other side
        worse_book = ""
        for book, outcomes in market.bookmaker_odds.items():
            if other_side in outcomes and book != better_book:
                worse_book = book
                break

        return value_side, better_book, worse_book, best_price

    def detect_all(self, markets: list[MarketOdds]) -> list[ArbResult]:
        """Run arb detection across all markets. Returns list of arb results."""
        arbs: list[ArbResult] = []
        for market in markets:
            result = self.detect(market)
            if result is not None:
                arbs.append(result)
        if arbs:
            logger.info("Found %d arbitrage opportunities", len(arbs))
        return arbs
