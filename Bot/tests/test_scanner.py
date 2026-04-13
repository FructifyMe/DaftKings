"""Tests for scanner module: OddsFetcher and ArbDetector."""

import pytest
from datetime import datetime, timezone

from src.scanner.odds_fetcher import OddsFetcher
from src.scanner.arb_detector import ArbDetector
from src.models import MarketOdds


# ── OddsFetcher.calculate_implied_prob ──────────────────────────────────────

class TestImpliedProbability:
    def test_negative_odds_110(self):
        assert abs(OddsFetcher.calculate_implied_prob(-110) - 0.5238) < 0.001

    def test_positive_odds_130(self):
        assert abs(OddsFetcher.calculate_implied_prob(130) - 0.4348) < 0.001

    def test_negative_odds_200(self):
        assert abs(OddsFetcher.calculate_implied_prob(-200) - 0.6667) < 0.001

    def test_positive_odds_200(self):
        assert abs(OddsFetcher.calculate_implied_prob(200) - 0.3333) < 0.001

    def test_heavy_favorite(self):
        prob = OddsFetcher.calculate_implied_prob(-500)
        assert 0.83 < prob < 0.84

    def test_big_underdog(self):
        prob = OddsFetcher.calculate_implied_prob(500)
        assert 0.16 < prob < 0.17

    def test_even_odds(self):
        assert abs(OddsFetcher.calculate_implied_prob(100) - 0.50) < 0.001

    def test_minus_100(self):
        assert abs(OddsFetcher.calculate_implied_prob(-100) - 0.50) < 0.001


# ── OddsFetcher API error handling ──────────────────────────────────────────

class TestOddsFetcherErrors:
    def test_no_api_key_returns_empty(self):
        fetcher = OddsFetcher(api_key="")
        result = fetcher.get_odds("basketball_nba")
        assert result == []

    def test_get_all_sports_with_no_key(self):
        fetcher = OddsFetcher(api_key="")
        result = fetcher.get_all_sports()
        assert result == []


# ── ArbDetector ─────────────────────────────────────────────────────────────

def _make_market(best_odds: dict, implied_probs: dict, bookmaker_odds: dict | None = None) -> MarketOdds:
    """Helper to create a MarketOdds for testing."""
    return MarketOdds(
        event_id="test_event",
        sport="basketball_nba",
        league="NBA",
        home_team="Lakers",
        away_team="Celtics",
        game_time=datetime.now(timezone.utc),
        market_type="h2h",
        bookmaker_odds=bookmaker_odds or {"book1": {"home": best_odds.get("home", 0), "away": best_odds.get("away", 0)}},
        best_odds=best_odds,
        implied_probs=implied_probs,
    )


class TestArbDetector:
    def setup_method(self):
        self.detector = ArbDetector()

    def test_no_arb_fair_market(self):
        """Both sides at -105 — sum ~102.4%, no arb."""
        market = _make_market(
            best_odds={"home": -105, "away": -105},
            implied_probs={"home": 0.512, "away": 0.512},
        )
        assert self.detector.detect(market) is None

    def test_no_arb_standard_vig(self):
        """Standard -110/-110 market — sum ~104.8%, no arb."""
        market = _make_market(
            best_odds={"home": -110, "away": -110},
            implied_probs={"home": 0.5238, "away": 0.5238},
        )
        assert self.detector.detect(market) is None

    def test_arb_detected(self):
        """Cross-book arb: implied probs sum to ~94.1%."""
        market = _make_market(
            best_odds={"home": 115, "away": 110},
            implied_probs={"home": 100 / 215, "away": 100 / 210},
            bookmaker_odds={
                "bookA": {"home": 115, "away": -140},
                "bookB": {"home": -130, "away": 110},
            },
        )
        result = self.detector.detect(market)
        assert result is not None
        assert result.arb_profit_pct > 0
        assert result.mispriced_side in ("home", "away")
        assert result.better_book in ("bookA", "bookB")

    def test_arb_identifies_correct_mispriced_side(self):
        """When home has lower implied prob, home should be flagged as value."""
        market = _make_market(
            best_odds={"home": 150, "away": 120},
            implied_probs={"home": 0.40, "away": 0.4545},
            bookmaker_odds={
                "bookA": {"home": 150, "away": -180},
                "bookB": {"home": -170, "away": 120},
            },
        )
        result = self.detector.detect(market)
        assert result is not None
        # home has lower implied prob (0.40 < 0.4545), so home is mispriced
        assert result.mispriced_side == "home"
        assert result.better_book == "bookA"

    def test_single_side_returns_none(self):
        market = _make_market(
            best_odds={"home": -110},
            implied_probs={"home": 0.5238},
        )
        assert self.detector.detect(market) is None

    def test_zero_prob_returns_none(self):
        market = _make_market(
            best_odds={"home": -110, "away": 100},
            implied_probs={"home": 0.0, "away": 0.5},
        )
        assert self.detector.detect(market) is None

    def test_detect_all(self):
        """detect_all processes a list and returns only arb results."""
        fair = _make_market({"home": -110, "away": -110}, {"home": 0.524, "away": 0.524})
        arb = _make_market(
            {"home": 150, "away": 120},
            {"home": 0.40, "away": 0.45},
            {"bookA": {"home": 150}, "bookB": {"away": 120}},
        )
        results = self.detector.detect_all([fair, arb])
        assert len(results) == 1
