"""Fetches live odds from The Odds API and normalizes into MarketOdds objects."""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from config import CONFIG
from src.models import MarketOdds

logger = logging.getLogger(__name__)

BOT_ROOT = Path(__file__).resolve().parent.parent.parent


def api_call_with_retry(func, *args, retries: int = 3, backoff: int = 2, **kwargs):
    """Retry wrapper with exponential backoff for external API calls."""
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == retries - 1:
                logger.error("API call failed after %d attempts: %s", retries, e)
                raise
            wait = backoff ** attempt
            logger.warning("Attempt %d failed, retrying in %ds: %s", attempt + 1, wait, e)
            time.sleep(wait)


class OddsFetcher:
    """Client for The Odds API. Fetches live/upcoming odds for all in-scope sports."""

    BASE_URL = "https://api.the-odds-api.com/v4"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or CONFIG.odds_api_key
        self.remaining_requests: int | None = None

    def get_odds(self, sport: str, markets: list[str] | None = None) -> list[MarketOdds]:
        """Fetch live odds for a sport. Returns normalized MarketOdds objects."""
        if not self.api_key:
            logger.error("ODDS_API_KEY not set — cannot fetch odds")
            return []

        markets = markets or ["h2h", "spreads", "totals"]
        params = {
            "apiKey": self.api_key,
            "regions": CONFIG.odds_api_regions,
            "markets": ",".join(markets),
            "oddsFormat": "american",
        }
        # Only filter by bookmaker if explicitly configured
        if CONFIG.bookmakers:
            params["bookmakers"] = ",".join(CONFIG.bookmakers)

        url = f"{self.BASE_URL}/sports/{sport}/odds"
        try:
            response = api_call_with_retry(
                requests.get, url, params=params, timeout=30,
                retries=CONFIG.api_retries, backoff=CONFIG.api_backoff,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error("Failed to fetch odds for %s: %s", sport, e)
            return []

        # Track remaining API credits
        self.remaining_requests = response.headers.get("x-requests-remaining")
        if self.remaining_requests is not None:
            logger.info("Odds API requests remaining: %s", self.remaining_requests)

        data = response.json()

        # Save raw response for historical data / ML training
        self._save_raw(sport, data)

        return self._parse_response(sport, data, markets)

    # Sports that use outrights instead of h2h/spreads/totals
    OUTRIGHT_SPORTS = {"golf_masters_tournament_winner", "golf_pga_championship_winner",
                       "golf_the_open_championship_winner", "golf_us_open_winner"}

    def get_all_sports(self) -> list[MarketOdds]:
        """Iterate all in-scope sports, return combined opportunity list."""
        all_markets: list[MarketOdds] = []
        for sport in CONFIG.active_sports:
            logger.info("Fetching odds for %s...", sport)
            try:
                # Golf futures use "outrights", tennis uses "h2h"
                if sport in self.OUTRIGHT_SPORTS:
                    markets = ["outrights"]
                elif sport.startswith("tennis_"):
                    markets = ["h2h"]
                else:
                    markets = None  # default h2h, spreads, totals
                odds = self.get_odds(sport, markets=markets)
                all_markets.extend(odds)
                logger.info("Got %d markets for %s", len(odds), sport)
            except Exception as e:
                logger.error("Scanner failed for %s, continuing: %s", sport, e)
        logger.info("Total markets fetched: %d across %d sports", len(all_markets), len(CONFIG.active_sports))
        return all_markets

    @staticmethod
    def calculate_implied_prob(american_odds: int) -> float:
        """Convert American odds to implied probability.

        Examples:
            -110 -> 0.5238 (52.38%)
            +130 -> 0.4348 (43.48%)
            -200 -> 0.6667 (66.67%)
            +200 -> 0.3333 (33.33%)
        """
        if american_odds < 0:
            return abs(american_odds) / (abs(american_odds) + 100)
        return 100 / (american_odds + 100)

    def _parse_response(self, sport: str, data: list[dict], markets: list[str]) -> list[MarketOdds]:
        """Parse The Odds API JSON response into MarketOdds objects."""
        results: list[MarketOdds] = []

        for event in data:
            event_id = event.get("id", "")
            home_team = event.get("home_team", "")
            away_team = event.get("away_team", "")
            game_time_str = event.get("commence_time", "")

            try:
                game_time = datetime.fromisoformat(game_time_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                game_time = datetime.now(timezone.utc)

            # Extract league from sport key (e.g., "basketball_nba" -> "NBA")
            league = sport.split("_")[-1].upper() if "_" in sport else sport.upper()

            # Process each market type from this event's bookmakers
            for market_type in markets:
                bookmaker_odds: dict[str, dict] = {}

                for bookmaker in event.get("bookmakers", []):
                    book_key = bookmaker.get("key", "")
                    for market in bookmaker.get("markets", []):
                        if market.get("key") != market_type:
                            continue
                        outcomes = {}
                        for outcome in market.get("outcomes", []):
                            name = outcome.get("name", "")
                            price = outcome.get("price")
                            point = outcome.get("point")
                            if price is not None:
                                key = name
                                if point is not None:
                                    key = f"{name} {point}"
                                outcomes[key] = price
                        if outcomes:
                            bookmaker_odds[book_key] = outcomes

                if not bookmaker_odds:
                    continue

                # Calculate best odds per side
                best_odds: dict[str, int] = {}
                all_sides: set[str] = set()
                for book_outcomes in bookmaker_odds.values():
                    all_sides.update(book_outcomes.keys())

                for side in all_sides:
                    prices = [
                        book_outcomes[side]
                        for book_outcomes in bookmaker_odds.values()
                        if side in book_outcomes
                    ]
                    if prices:
                        # Best odds = highest American odds (most favorable to bettor)
                        best_odds[side] = max(prices)

                # Calculate implied probabilities from best odds
                implied_probs = {
                    side: self.calculate_implied_prob(odds)
                    for side, odds in best_odds.items()
                }

                results.append(MarketOdds(
                    event_id=event_id,
                    sport=sport,
                    league=league,
                    home_team=home_team,
                    away_team=away_team,
                    game_time=game_time,
                    market_type=market_type,
                    bookmaker_odds=bookmaker_odds,
                    best_odds=best_odds,
                    implied_probs=implied_probs,
                ))

        return results

    def _save_raw(self, sport: str, data: list[dict]) -> None:
        """Save raw API response to data/historical/ for future ML training."""
        try:
            hist_dir = BOT_ROOT / "data" / "historical"
            hist_dir.mkdir(parents=True, exist_ok=True)
            date_str = datetime.now().strftime("%Y-%m-%d")
            filepath = hist_dir / f"{sport}_{date_str}.json"
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save raw odds data: %s", e)
