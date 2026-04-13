"""Tests for executor module: BetLogger CSV operations and paper mode execution."""

import csv
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

from src.executor.bet_logger import BetLogger, BETS_LOG, ARB_LOG, RUN_LOG
from src.executor.kalshi_executor import KalshiExecutor
from src.models import (
    AnalysisResult, ArbResult, BetOrder, BetResult, BettingOpportunity,
)


def _make_opp() -> BettingOpportunity:
    return BettingOpportunity(
        event_id="test_e1",
        sport="basketball_nba",
        league="NBA",
        home_team="Lakers",
        away_team="Celtics",
        game_time=datetime.now(timezone.utc) + timedelta(hours=5),
        market_type="h2h",
        bookmaker_odds={"dk": {"home": -110, "away": 105}},
        best_odds={"home": -110, "away": 105},
        implied_probs={"home": 0.524, "away": 0.488},
    )


def _make_analysis() -> AnalysisResult:
    return AnalysisResult(
        recommendation="bet",
        side="home",
        confidence=0.75,
        estimated_edge=0.07,
        estimated_true_probability=0.58,
        key_factors=["rest", "home court"],
        reasoning="Strong rest advantage.",
        raw_haiku_response="{}",
    )


def _make_arb() -> ArbResult:
    return ArbResult(
        event_id="arb_e1",
        sport="nfl",
        home_team="Chiefs",
        away_team="Ravens",
        market_type="h2h",
        mispriced_side="away",
        better_book="pointsbet",
        worse_book="draftkings",
        better_odds=155,
        implied_total=0.96,
        arb_profit_pct=4.0,
        value_recommendation="Bet Ravens +155 as value",
    )


# ── BetLogger ───────────────────────────────────────────────────────────────

class TestBetLogger:
    def test_log_bet_creates_csv(self, tmp_path):
        fake_bets = tmp_path / "bets_log.csv"
        with patch("src.executor.bet_logger.BETS_LOG", fake_bets), \
             patch("src.executor.bet_logger.ARB_LOG", tmp_path / "arb.csv"), \
             patch("src.executor.bet_logger.RUN_LOG", tmp_path / "run.csv"):
            bl = BetLogger("test_run")
            opp = _make_opp()
            analysis = _make_analysis()
            bet_order = BetOrder(opp, analysis, 17.50, True)
            bet_result = BetResult(bet_order, "paper", None, datetime.now(timezone.utc))

            bl.log(bet_result)

            assert fake_bets.exists()
            with open(fake_bets) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                assert len(rows) == 1
                assert rows[0]["sport"] == "basketball_nba"
                assert rows[0]["actual_stake_usd"] == "17.50"
                assert rows[0]["paper_mode"] == "True"

    def test_log_pass(self, tmp_path):
        fake_bets = tmp_path / "bets_log.csv"
        with patch("src.executor.bet_logger.BETS_LOG", fake_bets), \
             patch("src.executor.bet_logger.ARB_LOG", tmp_path / "arb.csv"), \
             patch("src.executor.bet_logger.RUN_LOG", tmp_path / "run.csv"):
            bl = BetLogger("test_run")
            opp = _make_opp()
            analysis = _make_analysis()
            analysis.recommendation = "pass"

            bl.log_pass(opp, analysis)

            with open(fake_bets) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                assert len(rows) == 1
                assert rows[0]["result"] == "pass"
                assert "PASS:" in rows[0]["haiku_reasoning"]

    def test_log_arb(self, tmp_path):
        fake_arb = tmp_path / "arb_log.csv"
        with patch("src.executor.bet_logger.BETS_LOG", tmp_path / "bets.csv"), \
             patch("src.executor.bet_logger.ARB_LOG", fake_arb), \
             patch("src.executor.bet_logger.RUN_LOG", tmp_path / "run.csv"):
            bl = BetLogger("test_run")
            arb = _make_arb()
            bl.log_arb(arb)

            assert fake_arb.exists()
            with open(fake_arb) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                assert len(rows) == 1
                assert rows[0]["mispriced_side"] == "away"
                assert rows[0]["better_book"] == "pointsbet"

    def test_log_run(self, tmp_path):
        fake_run = tmp_path / "run_log.csv"
        with patch("src.executor.bet_logger.BETS_LOG", tmp_path / "bets.csv"), \
             patch("src.executor.bet_logger.ARB_LOG", tmp_path / "arb.csv"), \
             patch("src.executor.bet_logger.RUN_LOG", fake_run):
            bl = BetLogger("test_run")
            bl.log_run(50, 2, 10, 1, 45.3, 0)

            assert fake_run.exists()
            with open(fake_run) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                assert len(rows) == 1
                assert rows[0]["markets_scanned"] == "50"
                assert rows[0]["bets_placed"] == "1"

    def test_get_todays_bets_empty(self, tmp_path):
        with patch("src.executor.bet_logger.BETS_LOG", tmp_path / "nonexistent.csv"):
            bl = BetLogger()
            df = bl.get_todays_bets()
            assert len(df) == 0

    def test_get_todays_bets_filters_by_date(self, tmp_path):
        fake_bets = tmp_path / "bets_log.csv"
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        with open(fake_bets, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "sport", "event_id"])
            writer.writerow([f"{today}T10:00:00", "nba", "e1"])
            writer.writerow([f"{yesterday}T10:00:00", "nfl", "e2"])

        with patch("src.executor.bet_logger.BETS_LOG", fake_bets):
            bl = BetLogger()
            df = bl.get_todays_bets()
            assert len(df) == 1
            assert df.iloc[0]["event_id"] == "e1"


# ── KalshiExecutor paper mode ──────────────────────────────────────────────

class TestKalshiExecutorPaper:
    def test_paper_bet_returns_paper_result(self):
        executor = KalshiExecutor()
        opp = _make_opp()
        analysis = _make_analysis()
        bet_order = BetOrder(opp, analysis, 17.50, paper_mode=True)

        result = executor.place_bet(bet_order)

        assert result.status == "paper"
        assert result.kalshi_order_id is None
        assert result.bet_order.stake_usd == 17.50
