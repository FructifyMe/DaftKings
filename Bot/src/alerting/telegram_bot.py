"""Telegram alerting for bet placements, arb detections, kill switch, and daily summaries."""

from __future__ import annotations

import logging

import requests

from typing import TYPE_CHECKING

from config import CONFIG
from src.models import ArbResult, BetResult, DailyStats

if TYPE_CHECKING:
    from src.executor.settlement import SettlementResult

logger = logging.getLogger(__name__)


class TelegramBot:
    """Sends formatted messages to a Telegram chat via Bot API."""

    API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self, token: str | None = None, chat_id: str | None = None):
        self.token = token or CONFIG.telegram_bot_token
        self.chat_id = chat_id or CONFIG.telegram_chat_id

    def send_bet_alert(self, bet_result: BetResult) -> bool:
        """Send formatted bet placed message."""
        opp = bet_result.bet_order.opportunity
        analysis = bet_result.bet_order.analysis
        mode = "PAPER" if bet_result.bet_order.paper_mode else "LIVE"

        # Build odds string for the recommended side
        side = analysis.side or "unknown"
        odds = opp.best_odds.get(side, "N/A")
        odds_str = f"{odds:+d}" if isinstance(odds, int) else str(odds)

        # Find which book has the best odds
        best_book = "best available"
        for book, outcomes in opp.bookmaker_odds.items():
            if side in outcomes and outcomes[side] == odds:
                best_book = book
                break

        message = (
            f"\U0001F3AF {mode} BET PLACED\n"
            f"Sport: {opp.league} | {opp.home_team} vs {opp.away_team}\n"
            f"Bet: {side} {odds_str} @ {best_book}\n"
            f"Stake: ${bet_result.bet_order.stake_usd:.2f} | "
            f"Edge: {analysis.estimated_edge:.1%} | "
            f"Confidence: {analysis.confidence:.0%}\n"
            f"Reasoning: {analysis.reasoning}\n"
            f"Bankroll: ${CONFIG.starting_bankroll - bet_result.bet_order.stake_usd:.2f} remaining"
        )
        return self._send(message)

    def send_arb_alert(self, arb_result: ArbResult) -> bool:
        """Send formatted arb detection message."""
        message = (
            f"\u26A1 ARB DETECTED\n"
            f"Sport: {arb_result.sport} | {arb_result.home_team} vs {arb_result.away_team}\n"
            f"Arb margin: {arb_result.arb_profit_pct:.1f}%\n"
            f"Value side: {arb_result.mispriced_side} {arb_result.better_odds:+d} "
            f"@ {arb_result.better_book} (mispriced)\n"
            f"Implied prob spread: {arb_result.implied_total:.1%} total "
            f"({(1 - arb_result.implied_total) * 100:.0f}% gap)\n"
            f"Action: Bet {arb_result.mispriced_side} {arb_result.better_odds:+d} "
            f"as value \u2014 do NOT bet both sides"
        )
        return self._send(message)

    def send_kill_switch_alert(self, daily_stats: DailyStats) -> bool:
        """Send kill switch activation message."""
        message = (
            f"\U0001F6D1 KILL SWITCH ACTIVATED\n"
            f"Reason: Daily drawdown limit reached ({daily_stats.drawdown_pct:.1%})\n"
            f"Bets today: {daily_stats.bets_placed} | P&L: ${daily_stats.pnl_usd:+.2f}\n"
            f"No further bets will be placed today."
        )
        return self._send(message)

    def send_daily_summary(self, daily_stats: DailyStats) -> bool:
        """Send end-of-day summary message."""
        message = (
            f"\U0001F4CA DAILY SUMMARY \u2014 {daily_stats.date}\n"
            f"Bets placed: {daily_stats.bets_placed}\n"
            f"P&L: ${daily_stats.pnl_usd:+.2f}\n"
            f"Drawdown: {daily_stats.drawdown_pct:.1%}\n"
            f"Bankroll: ${daily_stats.bankroll_remaining:.2f}\n"
            f"Kill switch: {'TRIGGERED' if daily_stats.kill_switch_active else 'Not triggered'}"
        )
        return self._send(message)

    def send_settlement_alert(self, result: SettlementResult) -> bool:
        """Send formatted bet settlement message."""
        emoji = {
            "win": "\u2705", "loss": "\u274C", "push": "\u27A1\uFE0F", "void": "\u26AA",
        }.get(result.result, "\u2753")

        message = (
            f"{emoji} BET {result.result.upper()}\n"
            f"Sport: {result.sport} | {result.home_team} vs {result.away_team}\n"
            f"Market: {result.market_type} | Side: {result.recommended_side}\n"
            f"Score: {result.score_summary}\n"
            f"Stake: ${result.stake_usd:.2f} | P&L: ${result.pnl_usd:+.2f}"
        )
        return self._send(message)

    def send_settlement_summary(self, results: list[SettlementResult]) -> bool:
        """Send summary of all settled bets in a batch."""
        if not results:
            return False

        wins = sum(1 for r in results if r.result == "win")
        losses = sum(1 for r in results if r.result == "loss")
        pushes = sum(1 for r in results if r.result == "push")
        total_pnl = sum(r.pnl_usd for r in results)

        lines = [f"\U0001F4B0 SETTLEMENT REPORT — {len(results)} bets graded"]
        lines.append(f"Record: {wins}W-{losses}L-{pushes}P | P&L: ${total_pnl:+.2f}")
        lines.append("")

        for r in results:
            emoji = {"win": "\u2705", "loss": "\u274C", "push": "\u27A1\uFE0F", "void": "\u26AA"}.get(r.result, "?")
            lines.append(
                f"{emoji} {r.sport} | {r.home_team} vs {r.away_team} | "
                f"{r.score_summary} | ${r.pnl_usd:+.2f}"
            )

        return self._send("\n".join(lines))

    def send_error(self, error_msg: str) -> bool:
        """Send critical error alert."""
        message = f"\u274C BOT ERROR\n{error_msg}"
        return self._send(message)

    def _send(self, message: str) -> bool:
        """Send a message via Telegram Bot API. Returns True on success."""
        if not self.token or not self.chat_id:
            logger.warning("Telegram not configured — skipping alert")
            return False

        url = self.API_URL.format(token=self.token)
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("Telegram message sent successfully")
            return True
        except requests.RequestException as e:
            logger.error("Failed to send Telegram message: %s", e)
            return False
