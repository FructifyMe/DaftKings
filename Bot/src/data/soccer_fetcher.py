"""Soccer data fetcher — ESPN public API (EPL + MLS, free, no key)."""

from __future__ import annotations

import logging

from src.data.base_fetcher import BaseFetcher

logger = logging.getLogger(__name__)

# ESPN league codes
LEAGUE_MAP = {
    "soccer_epl": ("eng.1", "soccer"),
    "soccer_usa_mls": ("usa.1", "soccer"),
}

BASE = "https://site.api.espn.com/apis/v2/sports/soccer"
SITE_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"


class SoccerFetcher(BaseFetcher):

    def get_standings(self, sport_key: str) -> list[dict] | None:
        league_info = LEAGUE_MAP.get(sport_key)
        if not league_info:
            return None
        league_id = league_info[0]
        cache_key = f"soccer:standings:{league_id}"
        data = self._cached_get(cache_key, f"{BASE}/{league_id}/standings")
        if not data:
            return None
        try:
            entries = []
            for child in data.get("children", []):
                for standing in child.get("standings", {}).get("entries", []):
                    entries.append(standing)
            if not entries:
                # Try flat structure
                for standing in data.get("standings", []):
                    for entry in standing.get("entries", []):
                        entries.append(entry)
            return entries
        except Exception as e:
            logger.warning("Failed to parse soccer standings: %s", e)
            return None

    def get_team_record(self, team_name: str, sport_key: str) -> dict | None:
        standings = self.get_standings(sport_key)
        if not standings:
            return None
        for entry in standings:
            entry_name = entry.get("team", {}).get("displayName", "")
            # Fuzzy match — ESPN names might differ slightly
            if team_name.lower() in entry_name.lower() or entry_name.lower() in team_name.lower():
                stats = {}
                for stat in entry.get("stats", []):
                    stats[stat.get("name", "")] = stat.get("displayValue", stat.get("value", ""))
                wins = stats.get("wins", "0")
                draws = stats.get("draws", "0")
                losses = stats.get("losses", "0")
                points = stats.get("points", "0")
                gf = stats.get("pointsFor", stats.get("goalsFor", "0"))
                ga = stats.get("pointsAgainst", stats.get("goalsAgainst", "0"))
                rank = stats.get("rank", entry.get("note", {}).get("rank", "?"))
                # Form string from recent results
                form = ""
                for stat in entry.get("stats", []):
                    if stat.get("name") == "record":
                        form = stat.get("displayValue", "")
                return {
                    "record": f"W{wins}-D{draws}-L{losses}",
                    "points": points,
                    "goal_diff": f"{gf}GF/{ga}GA",
                    "position": rank,
                    "win_pct": int(wins) / max(int(wins) + int(draws) + int(losses), 1),
                }
        return None

    def get_recent_results(self, team_name: str, sport_key: str, count: int = 5) -> list[dict]:
        league_info = LEAGUE_MAP.get(sport_key)
        if not league_info:
            return []
        league_id = league_info[0]
        # ESPN scoreboard for recent results
        cache_key = f"soccer:scoreboard:{league_id}"
        data = self._cached_get(cache_key, f"{SITE_BASE}/{league_id}/scoreboard")
        if not data:
            return []
        results = []
        for event in data.get("events", []):
            competitors = event.get("competitions", [{}])[0].get("competitors", [])
            if len(competitors) < 2:
                continue
            home = competitors[0]
            away = competitors[1]
            home_name = home.get("team", {}).get("displayName", "")
            away_name = away.get("team", {}).get("displayName", "")
            if team_name.lower() not in home_name.lower() and team_name.lower() not in away_name.lower():
                continue
            home_score = home.get("score", "0")
            away_score = away.get("score", "0")
            results.append({
                "home": home_name,
                "away": away_name,
                "home_score": home_score,
                "away_score": away_score,
                "date": event.get("date", ""),
            })
        return results[:count]
