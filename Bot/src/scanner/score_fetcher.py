"""Fetches completed game scores from The Odds API /scores endpoint."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

from config import CONFIG
from src.scanner.odds_fetcher import api_call_with_retry

logger = logging.getLogger(__name__)


@dataclass
class GameScore:
    """Final score for a completed game."""

    event_id: str
    sport: str
    home_team: str
    away_team: str
    home_score: int | None
    away_score: int | None
    completed: bool
    last_update: datetime | None

    @property
    def winner(self) -> str | None:
        """Returns 'home', 'away', or 'draw'. None if not completed."""
        if not self.completed or self.home_score is None or self.away_score is None:
            return None
        if self.home_score > self.away_score:
            return "home"
        if self.away_score > self.home_score:
            return "away"
        return "draw"

    @property
    def total_score(self) -> int | None:
        """Returns combined score. None if not completed."""
        if self.home_score is None or self.away_score is None:
            return None
        return self.home_score + self.away_score

    @property
    def margin(self) -> int | None:
        """Returns home_score - away_score (positive = home won by N). None if not completed."""
        if self.home_score is None or self.away_score is None:
            return None
        return self.home_score - self.away_score


class ScoreFetcher:
    """Fetches game scores from The Odds API /scores endpoint.

    The /scores endpoint returns completed=true for finished games,
    with scores as a list of {name, score} objects.
    Uses 1 API request per sport (costs same as /odds).
    """

    BASE_URL = "https://api.the-odds-api.com/v4"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or CONFIG.odds_api_key
        self.remaining_requests: int | None = None

    def get_scores(self, sport: str, days_from: int = 3) -> list[GameScore]:
        """Fetch scores for a sport. days_from controls how far back to look (1-3 days)."""
        if not self.api_key:
            logger.error("ODDS_API_KEY not set — cannot fetch scores")
            return []

        params = {
            "apiKey": self.api_key,
            "daysFrom": min(days_from, 3),  # API max is 3
        }

        url = f"{self.BASE_URL}/sports/{sport}/scores"
        try:
            response = api_call_with_retry(
                requests.get, url, params=params, timeout=30,
                retries=CONFIG.api_retries, backoff=CONFIG.api_backoff,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error("Failed to fetch scores for %s: %s", sport, e)
            return []

        self.remaining_requests = response.headers.get("x-requests-remaining")
        if self.remaining_requests is not None:
            logger.info("Odds API requests remaining (scores): %s", self.remaining_requests)

        return self._parse_scores(sport, response.json())

    def get_all_scores(self, days_from: int = 3) -> dict[str, GameScore]:
        """Fetch scores for all active sports. Returns {event_id: GameScore}."""
        scores: dict[str, GameScore] = {}
        # Skip outright/futures sports — they don't have traditional scores
        skip = {"golf_masters_tournament_winner", "golf_pga_championship_winner",
                "golf_the_open_championship_winner", "golf_us_open_winner"}

        for sport in CONFIG.active_sports:
            if sport in skip:
                continue
            logger.info("Fetching scores for %s...", sport)
            try:
                sport_scores = self.get_scores(sport, days_from=days_from)
                for gs in sport_scores:
                    if gs.completed:
                        scores[gs.event_id] = gs
                logger.info("Got %d completed games for %s", len([s for s in sport_scores if s.completed]), sport)
            except Exception as e:
                logger.error("Score fetch failed for %s: %s", sport, e)

        logger.info("Total completed games fetched: %d", len(scores))
        return scores

    def _parse_scores(self, sport: str, data: list[dict]) -> list[GameScore]:
        """Parse The Odds API /scores JSON response."""
        results: list[GameScore] = []

        for event in data:
            event_id = event.get("id", "")
            home_team = event.get("home_team", "")
            away_team = event.get("away_team", "")
            completed = event.get("completed", False)

            home_score = None
            away_score = None

            for score_obj in event.get("scores", []) or []:
                name = score_obj.get("name", "")
                score_str = score_obj.get("score")
                if score_str is None:
                    continue
                try:
                    score_val = int(score_str)
                except (ValueError, TypeError):
                    continue

                if name == home_team:
                    home_score = score_val
                elif name == away_team:
                    away_score = score_val

            last_update = None
            update_str = event.get("last_update")
            if update_str:
                try:
                    last_update = datetime.fromisoformat(update_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass

            results.append(GameScore(
                event_id=event_id,
                sport=sport,
                home_team=home_team,
                away_team=away_team,
                home_score=home_score,
                away_score=away_score,
                completed=completed,
                last_update=last_update,
            ))

        return results
