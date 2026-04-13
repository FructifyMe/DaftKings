"""Daily drawdown monitor and kill switch. Halts betting when limits are breached."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from config import CONFIG
from src.models import DailyStats

logger = logging.getLogger(__name__)

BOT_ROOT = Path(__file__).resolve().parent.parent.parent
BETS_LOG = BOT_ROOT / "data" / "logs" / "bets_log.csv"
KILL_SWITCH_LOG = BOT_ROOT / "data" / "logs" / "kill_switch.log"


class KillSwitch:
    """Monitors daily P&L and bet count. Activates kill switch when limits breached."""

    def is_active(self) -> bool:
        """Returns True if daily drawdown >= KILL_SWITCH_DRAWDOWN or bets >= MAX_DAILY_BETS."""
        stats = self.get_daily_stats()
        if stats.kill_switch_active:
            return True
        if stats.drawdown_pct >= CONFIG.kill_switch_drawdown:
            self.activate(
                f"Daily drawdown limit reached ({stats.drawdown_pct:.1%})"
            )
            return True
        if stats.bets_placed >= CONFIG.max_daily_bets:
            self.activate(
                f"Max daily bets reached ({stats.bets_placed}/{CONFIG.max_daily_bets})"
            )
            return True
        return False

    def get_daily_stats(self) -> DailyStats:
        """Returns today's aggregated stats from bets_log.csv."""
        today = datetime.now().strftime("%Y-%m-%d")
        default = DailyStats(
            date=today,
            bets_placed=0,
            total_staked=0.0,
            pnl_usd=0.0,
            drawdown_pct=0.0,
            bankroll_remaining=CONFIG.starting_bankroll,
            kill_switch_active=self._is_killed_today(),
        )

        if not BETS_LOG.exists():
            return default

        try:
            df = pd.read_csv(BETS_LOG)
            if df.empty or "timestamp" not in df.columns:
                return default

            today_bets = df[df["timestamp"].str.startswith(today)]
            if today_bets.empty:
                return default

            bets_placed = len(today_bets)
            total_staked = today_bets["actual_stake_usd"].sum() if "actual_stake_usd" in today_bets.columns else 0.0
            pnl = today_bets["pnl_usd"].sum() if "pnl_usd" in today_bets.columns else 0.0

            # Drawdown = losses / starting bankroll
            drawdown_pct = abs(min(pnl, 0)) / CONFIG.starting_bankroll if CONFIG.starting_bankroll > 0 else 0.0
            bankroll_remaining = CONFIG.starting_bankroll + pnl

            return DailyStats(
                date=today,
                bets_placed=bets_placed,
                total_staked=total_staked,
                pnl_usd=pnl,
                drawdown_pct=drawdown_pct,
                bankroll_remaining=bankroll_remaining,
                kill_switch_active=(
                    self._is_killed_today()
                    or drawdown_pct >= CONFIG.kill_switch_drawdown
                    or bets_placed >= CONFIG.max_daily_bets
                ),
            )
        except Exception as e:
            logger.error("Error reading bets log for kill switch: %s", e)
            return default

    def activate(self, reason: str) -> None:
        """Log kill switch activation. Flag for the day."""
        logger.critical("KILL SWITCH ACTIVATED: %s", reason)

        KILL_SWITCH_LOG.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().isoformat()
        with open(KILL_SWITCH_LOG, "a") as f:
            f.write(f"{timestamp} | KILL SWITCH ACTIVATED | {reason}\n")

    def _is_killed_today(self) -> bool:
        """Check if kill switch was already triggered today."""
        if not KILL_SWITCH_LOG.exists():
            return False
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            with open(KILL_SWITCH_LOG) as f:
                for line in f:
                    if today in line and "KILL SWITCH ACTIVATED" in line:
                        return True
            return False
        except Exception:
            return False
