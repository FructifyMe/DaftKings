"""Tests for analyzer module: ValueDetector and ClaudeAnalyzer."""

import pytest
from datetime import datetime, timedelta, timezone

from src.analyzer.value_detector import ValueDetector
from src.analyzer.claude_analyzer import ClaudeAnalyzer, AnalysisError
from src.models import BettingOpportunity


# ── ValueDetector pre_filter ────────────────────────────────────────────────

def _make_opp(**kwargs) -> BettingOpportunity:
    """Helper to create a test BettingOpportunity with sensible defaults."""
    defaults = dict(
        event_id="test_e1",
        sport="basketball_nba",
        league="NBA",
        home_team="Lakers",
        away_team="Celtics",
        game_time=datetime.now(timezone.utc) + timedelta(hours=5),
        market_type="h2h",
        bookmaker_odds={"dk": {"home": -110, "away": 105}},
        best_odds={"home": -110, "away": 105},
        implied_probs={"home": 0.524, "away": 0.488},  # sum=1.012
    )
    defaults.update(kwargs)
    return BettingOpportunity(**defaults)


class TestValueDetectorPreFilter:
    def setup_method(self):
        self.vd = ValueDetector()

    def test_valid_opportunity_passes(self):
        assert self.vd.pre_filter(_make_opp()) is True

    def test_single_side_fails(self):
        opp = _make_opp(best_odds={"home": -110}, implied_probs={"home": 0.524})
        assert self.vd.pre_filter(opp) is False

    def test_arbed_market_fails(self):
        """Sum of implied probs <= 1.0 means already arbed out."""
        opp = _make_opp(implied_probs={"home": 0.48, "away": 0.48})  # sum=0.96
        assert self.vd.pre_filter(opp) is False

    def test_extreme_favorite_fails(self):
        """No side between 25-75%."""
        opp = _make_opp(implied_probs={"home": 0.85, "away": 0.20})
        assert self.vd.pre_filter(opp) is False

    def test_game_too_far_out_fails(self):
        opp = _make_opp(game_time=datetime.now(timezone.utc) + timedelta(hours=48))
        assert self.vd.pre_filter(opp) is False

    def test_pga_exempt_from_24h(self):
        opp = _make_opp(
            sport="golf_pga",
            game_time=datetime.now(timezone.utc) + timedelta(hours=72),
        )
        assert self.vd.pre_filter(opp) is True

    def test_borderline_25pct_passes(self):
        opp = _make_opp(implied_probs={"home": 0.75, "away": 0.30})
        assert self.vd.pre_filter(opp) is True

    def test_borderline_just_under_25pct_fails(self):
        opp = _make_opp(implied_probs={"home": 0.76, "away": 0.24})
        assert self.vd.pre_filter(opp) is False


class TestValueDetectorEdgeEstimate:
    def setup_method(self):
        self.vd = ValueDetector()

    def test_base_edge_from_vig(self):
        opp = _make_opp()
        edge = self.vd.estimate_preliminary_edge(opp, {})
        assert edge > 0

    def test_rest_advantage_bonus(self):
        opp = _make_opp()
        edge_no_rest = self.vd.estimate_preliminary_edge(opp, {})
        edge_with_rest = self.vd.estimate_preliminary_edge(
            opp, {"home_rest_days": 4, "away_rest_days": 1}
        )
        assert edge_with_rest > edge_no_rest

    def test_b2b_bonus(self):
        opp = _make_opp()
        edge_no_b2b = self.vd.estimate_preliminary_edge(opp, {})
        edge_b2b = self.vd.estimate_preliminary_edge(opp, {"is_b2b": True})
        assert edge_b2b > edge_no_b2b

    def test_arb_flag_bonus(self):
        opp_no_arb = _make_opp(arb_flag=False)
        opp_arb = _make_opp(arb_flag=True)
        edge_no = self.vd.estimate_preliminary_edge(opp_no_arb, {})
        edge_yes = self.vd.estimate_preliminary_edge(opp_arb, {})
        assert edge_yes > edge_no

    def test_sort_by_edge(self):
        opps = [
            _make_opp(event_id="e1", arb_flag=False),
            _make_opp(event_id="e2", arb_flag=True),
            _make_opp(event_id="e3", arb_flag=False),
        ]
        factors = {"e1": {}, "e2": {}, "e3": {"is_b2b": True}}
        sorted_opps = self.vd.sort_by_edge(opps, factors)
        # e2 (arb) should rank higher than e3 (b2b) which ranks higher than e1 (nothing)
        assert sorted_opps[0].event_id == "e2"
        assert sorted_opps[1].event_id == "e3"
        assert sorted_opps[2].event_id == "e1"


# ── ClaudeAnalyzer.parse_response ───────────────────────────────────────────

class TestClaudeAnalyzerParse:
    def setup_method(self):
        self.analyzer = ClaudeAnalyzer()

    def test_valid_json_bet(self):
        raw = '{"recommendation":"bet","side":"home","confidence":0.75,"estimated_edge":0.07,"estimated_true_probability":0.58,"key_factors":["rest","home court"],"reasoning":"Strong edge."}'
        result = self.analyzer.parse_response(raw)
        assert result.recommendation == "bet"
        assert result.side == "home"
        assert result.confidence == 0.75
        assert result.estimated_edge == 0.07
        assert len(result.key_factors) == 2

    def test_valid_json_pass(self):
        raw = '{"recommendation":"pass","side":null,"confidence":0.45,"estimated_edge":0.02,"estimated_true_probability":0.50,"key_factors":["no edge"],"reasoning":"No value."}'
        result = self.analyzer.parse_response(raw)
        assert result.recommendation == "pass"
        assert result.side is None

    def test_code_fenced_json(self):
        raw = '```json\n{"recommendation":"bet","side":"away","confidence":0.80,"estimated_edge":0.06,"estimated_true_probability":0.55,"key_factors":[],"reasoning":"Good."}\n```'
        result = self.analyzer.parse_response(raw)
        assert result.recommendation == "bet"

    def test_invalid_json_raises(self):
        with pytest.raises(AnalysisError):
            self.analyzer.parse_response("not json at all")

    def test_missing_field_raises(self):
        with pytest.raises(AnalysisError):
            self.analyzer.parse_response('{"recommendation":"bet"}')

    def test_invalid_recommendation_raises(self):
        with pytest.raises(AnalysisError):
            self.analyzer.parse_response(
                '{"recommendation":"maybe","confidence":0.5,"estimated_edge":0.05,"reasoning":"test"}'
            )

    def test_empty_string_raises(self):
        with pytest.raises(AnalysisError):
            self.analyzer.parse_response("")

    def test_raw_response_preserved(self):
        raw = '{"recommendation":"pass","side":null,"confidence":0.3,"estimated_edge":0.01,"estimated_true_probability":0.48,"key_factors":[],"reasoning":"No value."}'
        result = self.analyzer.parse_response(raw)
        assert result.raw_haiku_response == raw
