"""Kalshi API client for fetching market data (read-only). Execution is in kalshi_executor.py."""

from __future__ import annotations

import logging

import requests

from config import CONFIG
from src.scanner.odds_fetcher import api_call_with_retry

logger = logging.getLogger(__name__)


class KalshiClient:
    """Client for Kalshi market data. Uses sandbox URL by default."""

    # Sport category slugs on Kalshi
    SPORT_CATEGORIES = {
        "americanfootball_nfl": "football",
        "basketball_nba": "basketball",
        "baseball_mlb": "baseball",
        "icehockey_nhl": "hockey",
        "golf_pga": "golf",
        "soccer_epl": "soccer",
        "soccer_usa_mls": "soccer",
    }

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or CONFIG.kalshi_api_key
        self.base_url = CONFIG.kalshi_base_url
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            })

    def get_markets(self, sport_category: str | None = None, limit: int = 100) -> list[dict]:
        """Fetch open Kalshi markets, optionally filtered by sport category.

        Returns raw market dicts from the Kalshi API.
        """
        if not self.api_key:
            logger.error("KALSHI_API_KEY not set — cannot fetch markets")
            return []

        params: dict = {
            "limit": limit,
            "status": "open",
        }
        if sport_category:
            # Map our sport key to Kalshi's category
            kalshi_cat = self.SPORT_CATEGORIES.get(sport_category, sport_category)
            params["series_ticker"] = kalshi_cat

        url = f"{self.base_url}/markets"
        try:
            response = api_call_with_retry(
                self.session.get, url, params=params, timeout=30,
                retries=CONFIG.api_retries, backoff=CONFIG.api_backoff,
            )
            response.raise_for_status()
            data = response.json()
            markets = data.get("markets", [])
            logger.info("Fetched %d Kalshi markets (category=%s)", len(markets), sport_category)
            return markets
        except requests.RequestException as e:
            logger.error("Failed to fetch Kalshi markets: %s", e)
            return []

    def get_market_price(self, market_id: str) -> dict | None:
        """Fetch current yes/no price for a specific Kalshi contract.

        Returns dict with 'yes_price', 'no_price', 'ticker', etc., or None on failure.
        """
        if not self.api_key:
            logger.error("KALSHI_API_KEY not set")
            return None

        url = f"{self.base_url}/markets/{market_id}"
        try:
            response = api_call_with_retry(
                self.session.get, url, timeout=30,
                retries=CONFIG.api_retries, backoff=CONFIG.api_backoff,
            )
            response.raise_for_status()
            market = response.json().get("market", {})
            return {
                "ticker": market.get("ticker"),
                "title": market.get("title"),
                "yes_price": market.get("yes_bid"),
                "no_price": market.get("no_bid"),
                "yes_ask": market.get("yes_ask"),
                "no_ask": market.get("no_ask"),
                "volume": market.get("volume"),
                "status": market.get("status"),
            }
        except requests.RequestException as e:
            logger.error("Failed to fetch Kalshi market %s: %s", market_id, e)
            return None

    def get_events(self, series_ticker: str | None = None, limit: int = 50) -> list[dict]:
        """Fetch Kalshi events (groups of related markets)."""
        if not self.api_key:
            logger.error("KALSHI_API_KEY not set")
            return []

        params: dict = {"limit": limit, "status": "open"}
        if series_ticker:
            params["series_ticker"] = series_ticker

        url = f"{self.base_url}/events"
        try:
            response = api_call_with_retry(
                self.session.get, url, params=params, timeout=30,
                retries=CONFIG.api_retries, backoff=CONFIG.api_backoff,
            )
            response.raise_for_status()
            events = response.json().get("events", [])
            logger.info("Fetched %d Kalshi events", len(events))
            return events
        except requests.RequestException as e:
            logger.error("Failed to fetch Kalshi events: %s", e)
            return []
