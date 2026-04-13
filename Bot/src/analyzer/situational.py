"""Enriches MarketOdds with real situational context from free sports APIs."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests

from config import CONFIG
from src.data.cache import CycleCache
from src.data.injury_fetcher import InjuryFetcher
from src.data.mlb_fetcher import MLBFetcher
from src.data.nba_fetcher import NBAFetcher
from src.data.nhl_fetcher import NHLFetcher
from src.data.soccer_fetcher import SoccerFetcher
from src.models import MarketOdds
from src.scanner.odds_fetcher import api_call_with_retry

logger = logging.getLogger(__name__)

# Venue coordinates for weather lookups (lat, lon).
VENUE_COORDS: dict[str, tuple[float, float]] = {
    # NFL
    "Arizona Cardinals": (33.5276, -112.2626), "Atlanta Falcons": (33.7554, -84.4010),
    "Baltimore Ravens": (39.2780, -76.6227), "Buffalo Bills": (42.7738, -78.7870),
    "Carolina Panthers": (35.2258, -80.8528), "Chicago Bears": (41.8623, -87.6167),
    "Cincinnati Bengals": (39.0955, -84.5161), "Cleveland Browns": (41.5061, -81.6995),
    "Dallas Cowboys": (32.7473, -97.0945), "Denver Broncos": (39.7439, -105.0201),
    "Detroit Lions": (42.3400, -83.0456), "Green Bay Packers": (44.5013, -88.0622),
    "Houston Texans": (29.6847, -95.4107), "Indianapolis Colts": (39.7601, -86.1639),
    "Jacksonville Jaguars": (30.3239, -81.6373), "Kansas City Chiefs": (39.0489, -94.4839),
    "Las Vegas Raiders": (36.0908, -115.1833), "Los Angeles Chargers": (33.9535, -118.3392),
    "Los Angeles Rams": (33.9535, -118.3392), "Miami Dolphins": (25.9580, -80.2389),
    "Minnesota Vikings": (44.9736, -93.2575), "New England Patriots": (42.0909, -71.2643),
    "New Orleans Saints": (29.9511, -90.0812), "New York Giants": (40.8128, -74.0742),
    "New York Jets": (40.8128, -74.0742), "Philadelphia Eagles": (39.9008, -75.1675),
    "Pittsburgh Steelers": (40.4468, -80.0158), "San Francisco 49ers": (37.4033, -121.9694),
    "Seattle Seahawks": (47.5952, -122.3316), "Tampa Bay Buccaneers": (27.9759, -82.5033),
    "Tennessee Titans": (36.1665, -86.7713), "Washington Commanders": (38.9076, -76.8645),
    # MLB
    "New York Yankees": (40.8296, -73.9262), "New York Mets": (40.7571, -73.8458),
    "Boston Red Sox": (42.3467, -71.0972), "Los Angeles Dodgers": (34.0739, -118.2400),
    "Chicago Cubs": (41.9484, -87.6553), "Chicago White Sox": (41.8300, -87.6339),
    "Houston Astros": (29.7572, -95.3554), "Atlanta Braves": (33.8911, -84.4682),
    "Philadelphia Phillies": (39.9061, -75.1665), "San Diego Padres": (32.7076, -117.1570),
    "Seattle Mariners": (47.5914, -122.3325), "San Francisco Giants": (37.7786, -122.3893),
    "St. Louis Cardinals": (38.6226, -90.1928), "Milwaukee Brewers": (43.0280, -87.9712),
    "Cleveland Guardians": (41.4962, -81.6852), "Texas Rangers": (32.7512, -97.0832),
    "Minnesota Twins": (44.9818, -93.2775), "Detroit Tigers": (42.3390, -83.0485),
    "Baltimore Orioles": (39.2838, -76.6218), "Toronto Blue Jays": (43.6414, -79.3894),
    "Tampa Bay Rays": (27.7682, -82.6534), "Kansas City Royals": (39.0517, -94.4803),
    "Colorado Rockies": (39.7559, -104.9942), "Arizona Diamondbacks": (33.4455, -112.0667),
    "Pittsburgh Pirates": (40.4469, -80.0057), "Cincinnati Reds": (39.0974, -84.5083),
    "Miami Marlins": (25.7781, -80.2196), "Los Angeles Angels": (33.8003, -117.8827),
    "Oakland Athletics": (37.7516, -122.2005), "Washington Nationals": (38.8730, -77.0074),
}

INDOOR_SPORTS = {"basketball_nba", "icehockey_nhl"}


class SituationalAnalyzer:
    """Enriches betting opportunities with real data from free sports APIs."""

    def __init__(self):
        self.cache = CycleCache()
        self.mlb = MLBFetcher(self.cache)
        self.nba = NBAFetcher(self.cache)
        self.nhl = NHLFetcher(self.cache)
        self.soccer = SoccerFetcher(self.cache)
        self.injuries = InjuryFetcher(self.cache)

    def enrich(self, market: MarketOdds) -> dict:
        """Build situational factors dict with real data from free APIs."""
        game_date = market.game_time.strftime("%Y-%m-%d")

        factors: dict = {
            "home_rest_days": None,
            "away_rest_days": None,
            "is_b2b": False,
            "weather": None,
            "home_advantage": CONFIG.home_advantage.get(market.sport, 0.0),
            "recent_form": "N/A",
            "sharp_signal": "N/A",
            "public_pct": "N/A",
            # New enriched fields
            "home_record": None,
            "away_record": None,
            "home_home_record": None,
            "away_away_record": None,
            "home_last_10": None,
            "away_last_10": None,
            "home_streak": None,
            "away_streak": None,
            "home_recent_results": None,
            "away_recent_results": None,
            "home_injuries": None,
            "away_injuries": None,
            "home_starter": None,
            "away_starter": None,
            "home_league_position": None,
            "away_league_position": None,
        }

        # Weather for outdoor sports
        if market.sport not in INDOOR_SPORTS and not market.sport.startswith("golf_"):
            weather = self._get_weather(market.home_team, market.game_time)
            if weather:
                factors["weather"] = weather

        # Sport-specific enrichment
        sport = market.sport
        try:
            if sport == "baseball_mlb":
                self._enrich_mlb(market, factors, game_date)
            elif sport == "basketball_nba":
                self._enrich_nba(market, factors, game_date)
            elif sport == "icehockey_nhl":
                self._enrich_nhl(market, factors, game_date)
            elif sport in ("soccer_epl", "soccer_usa_mls"):
                self._enrich_soccer(market, factors, sport)
        except Exception as e:
            logger.warning("Sport enrichment failed for %s %s: %s", sport, market.event_id, e)

        # Injuries (all major US sports)
        try:
            self._enrich_injuries(market, factors)
        except Exception as e:
            logger.warning("Injury enrichment failed for %s: %s", market.event_id, e)

        # Build recent_form summary from what we have
        factors["recent_form"] = self._build_form_summary(factors)

        return factors

    def _enrich_mlb(self, market: MarketOdds, factors: dict, game_date: str) -> None:
        """Enrich with MLB standings, pitcher matchups, rest days."""
        for side, team in [("home", market.home_team), ("away", market.away_team)]:
            rec = self.mlb.get_team_record(team)
            if rec:
                factors[f"{side}_record"] = rec["record"]
                factors[f"{side}_home_record" if side == "home" else f"{side}_away_record"] = (
                    rec["home_record"] if side == "home" else rec["away_record"]
                )
                factors[f"{side}_last_10"] = rec["last_10"]
                factors[f"{side}_streak"] = rec["streak"]

            rest = self.mlb.get_rest_days(team, game_date)
            if rest is not None:
                factors[f"{side}_rest_days"] = rest
                if rest == 0:
                    factors["is_b2b"] = True

            results = self.mlb.get_recent_results(team, count=5)
            if results:
                factors[f"{side}_recent_results"] = ", ".join(
                    f"{'W' if r['win'] else 'L'} {r['score']} vs {r['opponent'].split()[-1]}"
                    for r in results
                )

            starter = self.mlb.get_starter_summary(team, game_date)
            if starter:
                factors[f"{side}_starter"] = starter

    def _enrich_nba(self, market: MarketOdds, factors: dict, game_date: str) -> None:
        """Enrich with NBA standings, game logs, B2B detection."""
        for side, team in [("home", market.home_team), ("away", market.away_team)]:
            rec = self.nba.get_team_record(team)
            if rec:
                factors[f"{side}_record"] = rec["record"]
                factors[f"{side}_home_record" if side == "home" else f"{side}_away_record"] = (
                    rec["home_record"] if side == "home" else rec["away_record"]
                )
                factors[f"{side}_last_10"] = rec["last_10"]
                factors[f"{side}_streak"] = rec["streak"]

            rest = self.nba.get_rest_days(team, game_date)
            if rest is not None:
                factors[f"{side}_rest_days"] = rest

            b2b = self.nba.detect_b2b(team, game_date)
            if b2b:
                factors["is_b2b"] = True

            log = self.nba.get_team_game_log(team, count=5)
            if log:
                factors[f"{side}_recent_results"] = ", ".join(
                    f"{g['result']} {g['points']}pts ({g['matchup'].split()[-1]})"
                    for g in log
                )

    def _enrich_nhl(self, market: MarketOdds, factors: dict, game_date: str) -> None:
        """Enrich with NHL standings, recent results, rest days."""
        for side, team in [("home", market.home_team), ("away", market.away_team)]:
            rec = self.nhl.get_team_record(team)
            if rec:
                factors[f"{side}_record"] = rec["record"]
                factors[f"{side}_home_record" if side == "home" else f"{side}_away_record"] = (
                    rec["home_record"] if side == "home" else rec["away_record"]
                )
                factors[f"{side}_last_10"] = rec["last_10"]
                factors[f"{side}_streak"] = rec["streak"]

            rest = self.nhl.get_rest_days(team, game_date)
            if rest is not None:
                factors[f"{side}_rest_days"] = rest
                if rest <= 1:
                    factors["is_b2b"] = True

            results = self.nhl.get_recent_results(team, count=5)
            if results:
                factors[f"{side}_recent_results"] = ", ".join(
                    f"{'W' if r['win'] else 'L'} {r['score']} vs {r['opponent']}"
                    for r in results
                )

    def _enrich_soccer(self, market: MarketOdds, factors: dict, sport_key: str) -> None:
        """Enrich with soccer standings from ESPN."""
        for side, team in [("home", market.home_team), ("away", market.away_team)]:
            rec = self.soccer.get_team_record(team, sport_key)
            if rec:
                factors[f"{side}_record"] = rec["record"]
                factors[f"{side}_league_position"] = rec.get("position")
                # Soccer doesn't have home/away splits in ESPN free tier easily
                # but we have goal diff
                if side == "home":
                    factors["home_home_record"] = rec.get("goal_diff", "N/A")
                else:
                    factors["away_away_record"] = rec.get("goal_diff", "N/A")

    def _enrich_injuries(self, market: MarketOdds, factors: dict) -> None:
        """Enrich with injury data from ESPN."""
        sport = market.sport
        for side, team in [("home", market.home_team), ("away", market.away_team)]:
            summary = self.injuries.get_injury_summary(team, sport)
            if summary and summary != "No injuries reported":
                factors[f"{side}_injuries"] = summary

    def _build_form_summary(self, factors: dict) -> str:
        """Build a concise form summary from available data."""
        parts = []
        for side in ["home", "away"]:
            rec = factors.get(f"{side}_record")
            l10 = factors.get(f"{side}_last_10")
            streak = factors.get(f"{side}_streak")
            if rec:
                s = f"{side.title()}: {rec}"
                if l10:
                    s += f" L10:{l10}"
                if streak:
                    s += f" {streak}"
                parts.append(s)
        return " | ".join(parts) if parts else "N/A"

    def _get_weather(self, home_team: str, game_time: datetime) -> dict | None:
        """Fetch weather forecast from Open-Meteo for the venue at game time."""
        coords = VENUE_COORDS.get(home_team)
        if not coords:
            return None
        lat, lon = coords
        date_str = game_time.strftime("%Y-%m-%d")
        hour = game_time.hour

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat, "longitude": lon,
            "hourly": "temperature_2m,windspeed_10m,precipitation_probability",
            "start_date": date_str, "end_date": date_str,
            "temperature_unit": "fahrenheit", "windspeed_unit": "mph",
        }
        try:
            response = api_call_with_retry(
                requests.get, url, params=params, timeout=15, retries=2, backoff=2,
            )
            response.raise_for_status()
            data = response.json()
            hourly = data.get("hourly", {})
            temps = hourly.get("temperature_2m", [])
            winds = hourly.get("windspeed_10m", [])
            precip = hourly.get("precipitation_probability", [])
            idx = min(hour, len(temps) - 1) if temps else 0
            return {
                "temp_f": temps[idx] if idx < len(temps) else None,
                "wind_mph": winds[idx] if idx < len(winds) else None,
                "precipitation_pct": precip[idx] if idx < len(precip) else None,
            }
        except Exception as e:
            logger.warning("Weather lookup failed for %s: %s", home_team, e)
            return None
