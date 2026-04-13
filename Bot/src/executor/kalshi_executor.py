"""Kalshi order execution — paper and live modes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests

from config import CONFIG
from src.models import BetOrder, BetResult
from src.scanner.odds_fetcher import api_call_with_retry

logger = logging.getLogger(__name__)


class KalshiExecutor:
    """Places bets on Kalshi. Respects PAPER_MODE setting."""

    SANDBOX_URL = "https://demo-api.kalshi.co/trade-api/v2"
    LIVE_URL = "https://trading-api.kalshi.com/trade-api/v2"

    def __init__(self):
        self.session = requests.Session()
        if CONFIG.kalshi_api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {CONFIG.kalshi_api_key}",
                "Content-Type": "application/json",
            })

    @property
    def base_url(self) -> str:
        """Returns sandbox URL unless paper mode is explicitly off."""
        return self.SANDBOX_URL if CONFIG.paper_mode else self.LIVE_URL

    def place_bet(self, bet_order: BetOrder) -> BetResult:
        """Place a bet — paper or live depending on config.

        Paper mode: simulates placement, returns paper result.
        Live mode: calls Kalshi REST API to place order.
        Always returns a BetResult.
        """
        timestamp = datetime.now(timezone.utc)

        if bet_order.paper_mode:
            return self._paper_bet(bet_order, timestamp)
        else:
            return self._live_bet(bet_order, timestamp)

    def _paper_bet(self, bet_order: BetOrder, timestamp: datetime) -> BetResult:
        """Simulate a bet placement (no API call)."""
        opp = bet_order.opportunity
        logger.info(
            "PAPER BET: %s | %s @ %s | %s | side=%s | $%.2f",
            opp.sport, opp.away_team, opp.home_team,
            opp.market_type, bet_order.analysis.side, bet_order.stake_usd,
        )

        return BetResult(
            bet_order=bet_order,
            status="paper",
            kalshi_order_id=None,
            timestamp=timestamp,
        )

    def _live_bet(self, bet_order: BetOrder, timestamp: datetime) -> BetResult:
        """Place a real order via Kalshi REST API."""
        opp = bet_order.opportunity
        logger.info(
            "LIVE BET: %s | %s @ %s | %s | side=%s | $%.2f",
            opp.sport, opp.away_team, opp.home_team,
            opp.market_type, bet_order.analysis.side, bet_order.stake_usd,
        )

        # Convert to Kalshi order format
        # Kalshi uses yes/no contracts, not traditional sides
        side = "yes" if bet_order.analysis.side in ("home", "over") else "no"
        count = int(bet_order.stake_usd * 100)  # Kalshi uses cents

        payload = {
            "ticker": opp.event_id,
            "action": "buy",
            "side": side,
            "count": count,
            "type": "market",
        }

        url = f"{self.base_url}/portfolio/orders"
        try:
            response = api_call_with_retry(
                self.session.post, url, json=payload, timeout=30,
                retries=CONFIG.api_retries, backoff=CONFIG.api_backoff,
            )
            response.raise_for_status()
            data = response.json()
            order_id = data.get("order", {}).get("order_id", "unknown")

            logger.info("Order placed successfully. Kalshi order ID: %s", order_id)
            return BetResult(
                bet_order=bet_order,
                status="placed",
                kalshi_order_id=order_id,
                timestamp=timestamp,
            )
        except requests.RequestException as e:
            logger.error("Failed to place Kalshi order: %s", e)
            return BetResult(
                bet_order=bet_order,
                status="failed",
                kalshi_order_id=None,
                timestamp=timestamp,
            )
