"""Tests for risk manager: KellyCalculator, KillSwitch, PositionLimits."""

import csv
import os
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

from src.risk_manager.kelly import KellyCalculator
from src.risk_manager.kill_switch import KillSwitch, BETS_LOG, KILL_SWITCH_LOG
from src.risk_manager.position_limits import PositionLimits
from src.models import BettingOpportunity


# ── KellyCalculator ─────────────────────────────────────────────────────────

class TestKellyCalculator:
    def setup_method(self):
        self.kelly = KellyCalculator()

    def test_standard_quarter_kelly(self):
        """edge=0.07, bankroll=$1000, fraction=0.25, max=5% → $17.50"""
        assert self.kelly.calculate_stake(1000, 0.07, 0.25, 0.05) == 17.50

    def test_negative_edge_returns_zero(self):
        assert self.kelly.calculate_stake(1000, -0.01, 0.25, 0.05) == 0.0

    def test_zero_edge_returns_zero(self):
        assert self.kelly.calculate_stake(1000, 0.0, 0.25, 0.05) == 0.0

    def test_zero_bankroll_returns_zero(self):
        assert self.kelly.calculate_stake(0, 0.07, 0.25, 0.05) == 0.0

    def test_negative_bankroll_returns_zero(self):
        assert self.kelly.calculate_stake(-100, 0.07, 0.25, 0.05) == 0.0

    def test_cap_applied(self):
        """Large edge: 50% → raw=$125, cap=$50 → $50"""
        assert self.kelly.calculate_stake(1000, 0.50, 0.25, 0.05) == 50.0

    def test_small_edge(self):
        """edge=0.06 → raw=$15, cap=$50 → $15"""
        assert self.kelly.calculate_stake(1000, 0.06, 0.25, 0.05) == 15.0

    def test_rounding_to_half_dollar(self):
        """edge=0.03 → raw=7.50 → $7.50"""
        assert self.kelly.calculate_stake(1000, 0.03, 0.25, 0.05) == 7.50

    def test_full_kelly(self):
        """Full Kelly (fraction=1.0): edge=0.07, bankroll=$1000 → raw=$70, cap=$50"""
        assert self.kelly.calculate_stake(1000, 0.07, 1.0, 0.05) == 50.0

    def test_very_small_stake_rounds_to_zero(self):
        """edge=0.001 → raw=$0.25 → rounds to $0.50"""
        result = self.kelly.calculate_stake(1000, 0.001, 0.25, 0.05)
        assert result == 0.0  # 0.25 rounds to 0.5... let's check
        # Actually: 1000 * 0.001 * 0.25 = 0.25, round(0.25*2)/2 = round(0.5)/2 = 0.5/2 = 0.0
        # Hmm, round(0.5) in Python rounds to 0 (banker's rounding). Let's verify:
        # round(0.25 * 2) = round(0.5) = 0 → 0/2 = 0.0
        assert result == 0.0


# ── KillSwitch ──────────────────────────────────────────────────────────────

class TestKillSwitch:
    def setup_method(self):
        self.ks = KillSwitch()

    def test_no_bets_not_active(self):
        """With no bets log, kill switch should not be active."""
        # This may use real file — test against clean state
        if BETS_LOG.exists():
            pytest.skip("bets_log.csv exists — skip to avoid side effects")
        assert self.ks.is_active() is False

    def test_get_daily_stats_empty(self):
        if BETS_LOG.exists():
            pytest.skip("bets_log.csv exists")
        stats = self.ks.get_daily_stats()
        assert stats.bets_placed == 0
        assert stats.pnl_usd == 0.0
        assert stats.drawdown_pct == 0.0

    def test_drawdown_triggers_kill(self, tmp_path):
        """40%+ drawdown should trigger kill switch."""
        fake_log = tmp_path / "bets_log.csv"
        today = datetime.now().strftime("%Y-%m-%d")

        with open(fake_log, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "actual_stake_usd", "pnl_usd", "event_id"])
            # Two losing bets totaling -$420 on $1000 bankroll = 42% drawdown
            writer.writerow([f"{today}T10:00:00", "200", "-200", "e1"])
            writer.writerow([f"{today}T11:00:00", "220", "-220", "e2"])

        with patch("src.risk_manager.kill_switch.BETS_LOG", fake_log), \
             patch("src.risk_manager.kill_switch.KILL_SWITCH_LOG", tmp_path / "ks.log"):
            ks = KillSwitch()
            stats = ks.get_daily_stats()
            assert stats.drawdown_pct >= 0.40
            assert stats.kill_switch_active == True

    def test_under_drawdown_not_killed(self, tmp_path):
        """Under 40% drawdown should not trigger."""
        fake_log = tmp_path / "bets_log.csv"
        today = datetime.now().strftime("%Y-%m-%d")

        with open(fake_log, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "actual_stake_usd", "pnl_usd", "event_id"])
            writer.writerow([f"{today}T10:00:00", "100", "-50", "e1"])

        with patch("src.risk_manager.kill_switch.BETS_LOG", fake_log), \
             patch("src.risk_manager.kill_switch.KILL_SWITCH_LOG", tmp_path / "ks.log"):
            ks = KillSwitch()
            stats = ks.get_daily_stats()
            assert stats.drawdown_pct < 0.40
            assert stats.kill_switch_active == False


# ── PositionLimits ──────────────────────────────────────────────────────────

def _make_opp(**kwargs) -> BettingOpportunity:
    defaults = dict(
        event_id="test_e1",
        sport="basketball_nba",
        league="NBA",
        home_team="Lakers",
        away_team="Celtics",
        game_time=datetime.now(timezone.utc) + timedelta(hours=5),
        market_type="h2h",
        bookmaker_odds={},
        best_odds={},
        implied_probs={},
    )
    defaults.update(kwargs)
    return BettingOpportunity(**defaults)


class TestPositionLimits:
    def setup_method(self):
        self.pl = PositionLimits()

    def test_no_existing_bets_approved(self):
        opp = _make_opp()
        approved, reason = self.pl.check(opp)
        assert approved is True
        assert reason == "Approved"

    def test_correlated_bet_blocked(self, tmp_path):
        """Same team ML + spread should be blocked."""
        fake_log = tmp_path / "bets_log.csv"
        today = datetime.now().strftime("%Y-%m-%d")

        with open(fake_log, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "event_id", "sport", "home_team", "away_team", "market_type"])
            writer.writerow([f"{today}T10:00:00", "e1", "basketball_nba", "Lakers", "Celtics", "h2h"])

        opp = _make_opp(event_id="e2", market_type="spreads")

        with patch("src.risk_manager.position_limits.BETS_LOG", fake_log):
            pl = PositionLimits()
            approved, reason = pl.check(opp)
            assert approved is False
            assert "Correlated" in reason

    def test_same_game_blocked(self, tmp_path):
        """Can't have more than 1 bet on same game."""
        fake_log = tmp_path / "bets_log.csv"
        today = datetime.now().strftime("%Y-%m-%d")

        with open(fake_log, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "event_id", "sport", "home_team", "away_team", "market_type"])
            writer.writerow([f"{today}T10:00:00", "e1", "basketball_nba", "Lakers", "Celtics", "h2h"])

        opp = _make_opp(event_id="e1", market_type="totals")

        with patch("src.risk_manager.position_limits.BETS_LOG", fake_log):
            pl = PositionLimits()
            approved, reason = pl.check(opp)
            assert approved is False

    def test_sport_limit_blocked(self, tmp_path):
        """Max 2 bets per sport per day."""
        fake_log = tmp_path / "bets_log.csv"
        today = datetime.now().strftime("%Y-%m-%d")

        with open(fake_log, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "event_id", "sport", "home_team", "away_team", "market_type"])
            writer.writerow([f"{today}T10:00:00", "e1", "basketball_nba", "Lakers", "Celtics", "h2h"])
            writer.writerow([f"{today}T11:00:00", "e2", "basketball_nba", "Warriors", "Nets", "h2h"])

        opp = _make_opp(event_id="e3", home_team="Bucks", away_team="Heat")

        with patch("src.risk_manager.position_limits.BETS_LOG", fake_log):
            pl = PositionLimits()
            approved, reason = pl.check(opp)
            assert approved is False
            assert "basketball_nba" in reason

    def test_golf_outright_cap(self):
        opp = _make_opp(sport="golf_pga", market_type="outrights")
        # $25 stake on $1000 bankroll with 2% cap ($20) → blocked
        approved, reason = self.pl.check(opp, stake_usd=25.0)
        assert approved is False
        assert "Golf outright" in reason
