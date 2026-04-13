"""NHL data fetcher — api-web.nhle.com (free, no key, no rate limit)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from src.data.base_fetcher import BaseFetcher

logger = logging.getLogger(__name__)

# The Odds API team name -> NHL 3-letter abbreviation
NHL_TEAM_ABBREVS = {
    "Anaheim Ducks": "ANA", "Arizona Coyotes": "ARI", "Boston Bruins": "BOS",
    "Buffalo Sabres": "BUF", "Calgary Flames": "CGY", "Carolina Hurricanes": "CAR",
    "Chicago Blackhawks": "CHI", "Colorado Avalanche": "COL", "Columbus Blue Jackets": "CBJ",
    "Dallas Stars": "DAL", "Detroit Red Wings": "DET", "Edmonton Oilers": "EDM",
    "Florida Panthers": "FLA", "Los Angeles Kings": "LAK", "Minnesota Wild": "MIN",
    "Montreal Canadiens": "MTL", "Nashville Predators": "NSH", "New Jersey Devils": "NJD",
    "New York Islanders": "NYI", "New York Rangers": "NYR", "Ottawa Senators": "OTT",
    "Philadelphia Flyers": "PHI", "Pittsburgh Penguins": "PIT", "San Jose Sharks": "SJS",
    "Seattle Kraken": "SEA", "St. Louis Blues": "STL", "Tampa Bay Lightning": "TBL",
    "Toronto Maple Leafs": "TOR", "Utah Hockey Club": "UTA", "Vancouver Canucks": "VAN",
    "Vegas Golden Knights": "VGK", "Washington Capitals": "WSH", "Winnipeg Jets": "WPG",
}

BASE = "https://api-web.nhle.com/v1"


class NHLFetcher(BaseFetcher):

    def get_standings(self) -> list[dict] | None:
        data = self._cached_get("nhl:standings", f"{BASE}/standings/now")
        if not data:
            return None
        return data.get("standings", [])

    def get_team_record(self, team_name: str) -> dict | None:
        abbrev = NHL_TEAM_ABBREVS.get(team_name)
        if not abbrev:
            return None
        standings = self.get_standings()
        if not standings:
            return None
        for team in standings:
            if team.get("teamAbbrev", {}).get("default") == abbrev:
                w = team.get("wins", 0)
                l = team.get("losses", 0)
                otl = team.get("otLosses", 0)
                hw = team.get("homeWins", 0)
                hl = team.get("homeLosses", 0)
                hotl = team.get("homeOtLosses", 0)
                rw = team.get("roadWins", 0)
                rl = team.get("roadLosses", 0)
                rotl = team.get("roadOtLosses", 0)
                streak_code = team.get("streakCode", "")
                streak_count = team.get("streakCount", 0)
                l10w = team.get("l10Wins", 0)
                l10l = team.get("l10Losses", 0)
                l10otl = team.get("l10OtLosses", 0)
                return {
                    "record": f"{w}-{l}-{otl}",
                    "home_record": f"{hw}-{hl}-{hotl}",
                    "away_record": f"{rw}-{rl}-{rotl}",
                    "last_10": f"{l10w}-{l10l}-{l10otl}",
                    "streak": f"{streak_code}{streak_count}",
                    "points": team.get("points", 0),
                    "win_pct": w / max(w + l + otl, 1),
                }
        return None

    def get_recent_results(self, team_name: str, count: int = 5) -> list[dict]:
        abbrev = NHL_TEAM_ABBREVS.get(team_name)
        if not abbrev:
            return []
        cache_key = f"nhl:schedule:{abbrev}"
        data = self._cached_get(cache_key, f"{BASE}/club-schedule-season/{abbrev}/now")
        if not data:
            return []
        games = data.get("games", [])
        played = [g for g in games if g.get("gameState") in ("OFF", "FINAL")]
        recent = played[-count:] if played else []
        results = []
        for g in reversed(recent):
            home = g.get("homeTeam", {})
            away = g.get("awayTeam", {})
            home_score = home.get("score", 0)
            away_score = away.get("score", 0)
            is_home = home.get("abbrev") == abbrev
            opponent = away.get("abbrev", "?") if is_home else home.get("abbrev", "?")
            our_score = home_score if is_home else away_score
            opp_score = away_score if is_home else home_score
            win = our_score > opp_score
            results.append({
                "date": g.get("gameDate", ""),
                "opponent": opponent,
                "score": f"{our_score}-{opp_score}",
                "win": win,
                "home": is_home,
            })
        return results

    def get_rest_days(self, team_name: str, game_date: str) -> int | None:
        results = self.get_recent_results(team_name, count=3)
        if not results:
            return None
        last_date_str = results[0].get("date", "")
        if not last_date_str:
            return None
        try:
            last_date = datetime.strptime(last_date_str[:10], "%Y-%m-%d")
            target = datetime.strptime(game_date[:10], "%Y-%m-%d")
            return (target - last_date).days
        except ValueError:
            return None
