"""NBA data fetcher — stats.nba.com (free, no key, 0.6s rate limit)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from src.data.base_fetcher import BaseFetcher

logger = logging.getLogger(__name__)

# stats.nba.com requires these headers or it returns 403
NBA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.nba.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.nba.com",
}

BASE = "https://stats.nba.com/stats"
RATE_DELAY = 0.7  # seconds between calls

# The Odds API team name -> NBA team ID
NBA_TEAM_IDS = {
    "Atlanta Hawks": 1610612737, "Boston Celtics": 1610612738,
    "Brooklyn Nets": 1610612751, "Charlotte Hornets": 1610612766,
    "Chicago Bulls": 1610612741, "Cleveland Cavaliers": 1610612739,
    "Dallas Mavericks": 1610612742, "Denver Nuggets": 1610612743,
    "Detroit Pistons": 1610612765, "Golden State Warriors": 1610612744,
    "Houston Rockets": 1610612745, "Indiana Pacers": 1610612754,
    "Los Angeles Clippers": 1610612746, "Los Angeles Lakers": 1610612747,
    "Memphis Grizzlies": 1610612763, "Miami Heat": 1610612748,
    "Milwaukee Bucks": 1610612749, "Minnesota Timberwolves": 1610612750,
    "New Orleans Pelicans": 1610612740, "New York Knicks": 1610612752,
    "Oklahoma City Thunder": 1610612760, "Orlando Magic": 1610612753,
    "Philadelphia 76ers": 1610612755, "Phoenix Suns": 1610612756,
    "Portland Trail Blazers": 1610612757, "Sacramento Kings": 1610612758,
    "San Antonio Spurs": 1610612759, "Toronto Raptors": 1610612761,
    "Utah Jazz": 1610612762, "Washington Wizards": 1610612764,
}

# Reverse lookup for team ID -> short name
NBA_TEAM_NAMES = {v: k for k, v in NBA_TEAM_IDS.items()}


class NBAFetcher(BaseFetcher):

    def get_standings(self) -> dict | None:
        """Fetch league standings. Returns raw response with resultSets."""
        season = self._current_season()
        return self._cached_get(
            f"nba:standings:{season}",
            f"{BASE}/leaguestandingsv3",
            params={"LeagueID": "00", "Season": season, "SeasonType": "Regular Season"},
            headers=NBA_HEADERS,
            delay=RATE_DELAY,
        )

    def get_team_record(self, team_name: str) -> dict | None:
        team_id = NBA_TEAM_IDS.get(team_name)
        if not team_id:
            return None
        standings = self.get_standings()
        if not standings:
            return None
        try:
            result_sets = standings.get("resultSets", [])
            if not result_sets:
                return None
            headers = result_sets[0].get("headers", [])
            rows = result_sets[0].get("rowSet", [])
            for row in rows:
                row_dict = dict(zip(headers, row))
                if row_dict.get("TeamID") == team_id:
                    w = row_dict.get("WINS", 0)
                    l = row_dict.get("LOSSES", 0)
                    pct = row_dict.get("WinPCT", 0.0)
                    hw = row_dict.get("HomeRecord", "?")
                    aw = row_dict.get("RoadRecord", "?")
                    l10 = row_dict.get("L10", "?")
                    streak = row_dict.get("CurrentStreak", "?")
                    return {
                        "record": f"{w}-{l} ({pct:.3f})",
                        "home_record": hw,
                        "away_record": aw,
                        "last_10": l10,
                        "streak": str(streak),
                        "win_pct": float(pct),
                    }
        except Exception as e:
            logger.warning("Failed to parse NBA standings: %s", e)
        return None

    def get_team_game_log(self, team_name: str, count: int = 5) -> list[dict]:
        team_id = NBA_TEAM_IDS.get(team_name)
        if not team_id:
            return []
        season = self._current_season()
        cache_key = f"nba:gamelog:{team_id}"
        data = self._cached_get(
            cache_key,
            f"{BASE}/teamgamelog",
            params={"TeamID": team_id, "Season": season, "SeasonType": "Regular Season"},
            headers=NBA_HEADERS,
            delay=RATE_DELAY,
        )
        if not data:
            return []
        try:
            result_sets = data.get("resultSets", [])
            if not result_sets:
                return []
            headers = result_sets[0].get("headers", [])
            rows = result_sets[0].get("rowSet", [])
            games = []
            for row in rows[:count]:
                row_dict = dict(zip(headers, row))
                matchup = row_dict.get("MATCHUP", "")
                wl = row_dict.get("WL", "")
                pts = row_dict.get("PTS", 0)
                games.append({
                    "date": row_dict.get("GAME_DATE", ""),
                    "matchup": matchup,
                    "result": wl,
                    "points": pts,
                })
            return games
        except Exception as e:
            logger.warning("Failed to parse NBA game log: %s", e)
            return []

    def get_rest_days(self, team_name: str, game_date: str) -> int | None:
        log = self.get_team_game_log(team_name, count=2)
        if not log:
            return None
        last_date_str = log[0].get("date", "")
        if not last_date_str:
            return None
        try:
            # NBA game log dates are like "APR 08, 2026"
            last_date = datetime.strptime(last_date_str, "%b %d, %Y")
            target = datetime.strptime(game_date[:10], "%Y-%m-%d")
            return (target - last_date).days
        except ValueError:
            return None

    def detect_b2b(self, team_name: str, game_date: str) -> bool:
        rest = self.get_rest_days(team_name, game_date)
        return rest == 1 if rest is not None else False

    @staticmethod
    def _current_season() -> str:
        now = datetime.now()
        year = now.year if now.month >= 10 else now.year - 1
        return f"{year}-{str(year + 1)[-2:]}"
