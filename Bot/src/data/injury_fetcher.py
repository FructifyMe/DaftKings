"""Injury data fetcher — ESPN public API (all major US sports, free, no key)."""

from __future__ import annotations

import logging

from src.data.base_fetcher import BaseFetcher

logger = logging.getLogger(__name__)

# Sport key -> ESPN sport path
SPORT_MAP = {
    "americanfootball_nfl": "football/nfl",
    "basketball_nba": "basketball/nba",
    "baseball_mlb": "baseball/mlb",
    "icehockey_nhl": "hockey/nhl",
}

BASE = "https://site.api.espn.com/apis/site/v2/sports"

# Common team name lookups for ESPN team IDs
# We'll resolve by searching the injuries endpoint for team name matches
ESPN_TEAM_IDS: dict[str, dict[str, int]] = {}  # populated lazily


class InjuryFetcher(BaseFetcher):

    def get_league_injuries(self, sport_key: str) -> dict | None:
        """Fetch all injuries for a sport. Returns raw ESPN response."""
        sport_path = SPORT_MAP.get(sport_key)
        if not sport_path:
            return None
        cache_key = f"injuries:{sport_key}"
        return self._cached_get(cache_key, f"{BASE}/{sport_path}/injuries")

    def get_team_injuries(self, team_name: str, sport_key: str) -> list[dict]:
        """Returns list of injured players for a team."""
        data = self.get_league_injuries(sport_key)
        if not data:
            return []
        # ESPN injuries response has items with team info and injuries array
        for item in data.get("items", []):
            espn_team_name = item.get("team", {}).get("displayName", "")
            if team_name.lower() in espn_team_name.lower() or espn_team_name.lower() in team_name.lower():
                injuries = []
                for inj in item.get("injuries", []):
                    status = inj.get("status", "")
                    athlete = inj.get("athlete", {})
                    injuries.append({
                        "player": athlete.get("displayName", "Unknown"),
                        "position": athlete.get("position", {}).get("abbreviation", ""),
                        "status": status,
                        "detail": inj.get("longComment", inj.get("shortComment", "")),
                    })
                return injuries
        return []

    def get_injury_summary(self, team_name: str, sport_key: str) -> str:
        """Human-readable summary like 'OUT: J.Embiid (knee). DTD: T.Maxey (ankle)'."""
        injuries = self.get_team_injuries(team_name, sport_key)
        if not injuries:
            return "No injuries reported"

        by_status: dict[str, list[str]] = {}
        for inj in injuries:
            status = inj["status"].upper()
            if status in ("OUT", "DOUBTFUL", "QUESTIONABLE", "DAY-TO-DAY", "DTD",
                          "10-DAY IL", "15-DAY IL", "60-DAY IL", "INJURED RESERVE", "IR"):
                short_status = status.replace("INJURED RESERVE", "IR").replace("DAY-TO-DAY", "DTD")
                detail = inj["detail"][:30] if inj["detail"] else ""
                player_str = f"{inj['player']} ({inj['position']})"
                if detail:
                    player_str += f" - {detail}"
                by_status.setdefault(short_status, []).append(player_str)

        if not by_status:
            return "No significant injuries"

        parts = []
        for status in ["OUT", "IR", "15-DAY IL", "60-DAY IL", "DTD", "DOUBTFUL", "QUESTIONABLE"]:
            if status in by_status:
                players = ", ".join(by_status[status][:3])  # cap at 3 per status
                if len(by_status[status]) > 3:
                    players += f" +{len(by_status[status]) - 3} more"
                parts.append(f"{status}: {players}")
        return ". ".join(parts) if parts else "No significant injuries"
