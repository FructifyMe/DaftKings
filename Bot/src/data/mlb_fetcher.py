"""MLB data fetcher — statsapi.mlb.com (free, no key, no rate limit)."""

from __future__ import annotations

import logging
from datetime import datetime

from src.data.base_fetcher import BaseFetcher

logger = logging.getLogger(__name__)

BASE = "https://statsapi.mlb.com/api/v1"

# The Odds API team name -> MLB team ID
MLB_TEAM_IDS = {
    "Arizona Diamondbacks": 109, "Atlanta Braves": 144, "Baltimore Orioles": 110,
    "Boston Red Sox": 111, "Chicago Cubs": 112, "Chicago White Sox": 145,
    "Cincinnati Reds": 113, "Cleveland Guardians": 114, "Colorado Rockies": 115,
    "Detroit Tigers": 116, "Houston Astros": 117, "Kansas City Royals": 118,
    "Los Angeles Angels": 108, "Los Angeles Dodgers": 119, "Miami Marlins": 146,
    "Milwaukee Brewers": 158, "Minnesota Twins": 142, "New York Mets": 121,
    "New York Yankees": 147, "Oakland Athletics": 133, "Athletics": 133,
    "Philadelphia Phillies": 143, "Pittsburgh Pirates": 134, "San Diego Padres": 135,
    "San Francisco Giants": 137, "Seattle Mariners": 136, "St. Louis Cardinals": 138,
    "Tampa Bay Rays": 139, "Texas Rangers": 140, "Toronto Blue Jays": 141,
    "Washington Nationals": 120,
}


class MLBFetcher(BaseFetcher):

    def get_standings(self) -> list[dict] | None:
        data = self._cached_get(
            "mlb:standings",
            f"{BASE}/standings",
            params={"leagueId": "103,104", "season": str(datetime.now().year)},
        )
        if not data:
            return None
        records = []
        for div in data.get("records", []):
            for team_rec in div.get("teamRecords", []):
                records.append(team_rec)
        return records

    def get_team_record(self, team_name: str) -> dict | None:
        team_id = MLB_TEAM_IDS.get(team_name)
        if not team_id:
            return None
        standings = self.get_standings()
        if not standings:
            return None
        for rec in standings:
            if rec.get("team", {}).get("id") == team_id:
                w = rec.get("wins", 0)
                l = rec.get("losses", 0)
                pct = rec.get("winningPercentage", ".000")
                streak = rec.get("streak", {}).get("streakCode", "")
                # Extract splits
                splits = {}
                for split in rec.get("records", {}).get("splitRecords", []):
                    splits[split.get("type")] = f"{split.get('wins', 0)}-{split.get('losses', 0)}"
                home_rec = splits.get("home", "?")
                away_rec = splits.get("away", "?")
                last_10 = splits.get("lastTen", "?")
                return {
                    "record": f"{w}-{l} ({pct})",
                    "home_record": home_rec,
                    "away_record": away_rec,
                    "last_10": last_10,
                    "streak": streak,
                    "win_pct": float(pct) if pct != ".000" else 0.0,
                }
        return None

    def get_probable_pitchers(self, game_date: str) -> dict:
        """Returns {team_id: {name, era, ...}} for all games on date."""
        cache_key = f"mlb:schedule:{game_date}"
        data = self._cached_get(
            cache_key,
            f"{BASE}/schedule",
            params={
                "sportId": 1,
                "date": game_date,
                "hydrate": "probablePitcher(note)",
            },
        )
        if not data:
            return {}
        pitchers = {}
        for date_entry in data.get("dates", []):
            for game in date_entry.get("games", []):
                for side in ("home", "away"):
                    team_data = game.get("teams", {}).get(side, {})
                    team_id = team_data.get("team", {}).get("id")
                    pitcher = team_data.get("probablePitcher")
                    if pitcher and team_id:
                        pitchers[team_id] = {
                            "id": pitcher.get("id"),
                            "name": pitcher.get("fullName", "TBD"),
                        }
        return pitchers

    def get_pitcher_stats(self, pitcher_id: int) -> dict | None:
        """Get season stats + last 3 game logs for a pitcher."""
        cache_key = f"mlb:pitcher:{pitcher_id}"
        data = self._cached_get(
            cache_key,
            f"{BASE}/people/{pitcher_id}/stats",
            params={"stats": "season,gameLog", "group": "pitching",
                    "season": str(datetime.now().year)},
        )
        if not data:
            return None
        season_stats = None
        game_log = []
        for stat_group in data.get("stats", []):
            splits = stat_group.get("splits", [])
            if stat_group.get("type", {}).get("displayName") == "season" and splits:
                s = splits[0].get("stat", {})
                season_stats = {
                    "era": s.get("era", "-.--"),
                    "whip": s.get("whip", "-.--"),
                    "wins": s.get("wins", 0),
                    "losses": s.get("losses", 0),
                    "innings": s.get("inningsPitched", "0"),
                    "strikeouts": s.get("strikeOuts", 0),
                }
            elif stat_group.get("type", {}).get("displayName") == "gameLog":
                for split in splits[:3]:
                    s = split.get("stat", {})
                    game_log.append({
                        "date": split.get("date", ""),
                        "ip": s.get("inningsPitched", "0"),
                        "er": s.get("earnedRuns", 0),
                        "k": s.get("strikeOuts", 0),
                        "opponent": split.get("opponent", {}).get("name", "?"),
                    })
        if not season_stats:
            return None
        season_stats["recent_starts"] = game_log
        return season_stats

    def get_starter_summary(self, team_name: str, game_date: str) -> str | None:
        """Returns formatted pitcher summary like 'G.Cole (3.12 ERA, 1.05 WHIP, last 3: ...)'"""
        team_id = MLB_TEAM_IDS.get(team_name)
        if not team_id:
            return None
        pitchers = self.get_probable_pitchers(game_date)
        pitcher_info = pitchers.get(team_id)
        if not pitcher_info:
            return "TBD"
        stats = self.get_pitcher_stats(pitcher_info["id"])
        if not stats:
            return pitcher_info["name"]
        recent = ", ".join(
            f"{g['ip']}IP/{g['er']}ER/{g['k']}K"
            for g in stats.get("recent_starts", [])
        )
        return (
            f"{pitcher_info['name']} ({stats['era']} ERA, {stats['whip']} WHIP, "
            f"{stats['wins']}-{stats['losses']}"
            f"{', last 3: ' + recent if recent else ''})"
        )

    def get_recent_results(self, team_name: str, count: int = 5) -> list[dict]:
        team_id = MLB_TEAM_IDS.get(team_name)
        if not team_id:
            return []
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"mlb:results:{team_id}"
        data = self._cached_get(
            cache_key,
            f"{BASE}/schedule",
            params={"sportId": 1, "teamId": team_id, "endDate": today,
                    "startDate": "2026-03-01", "gameType": "R"},
        )
        if not data:
            return []
        games = []
        for date_entry in data.get("dates", []):
            for game in date_entry.get("games", []):
                if game.get("status", {}).get("detailedState") != "Final":
                    continue
                home = game.get("teams", {}).get("home", {})
                away = game.get("teams", {}).get("away", {})
                is_home = home.get("team", {}).get("id") == team_id
                our_score = home.get("score", 0) if is_home else away.get("score", 0)
                opp_score = away.get("score", 0) if is_home else home.get("score", 0)
                opp_name = away.get("team", {}).get("name", "?") if is_home else home.get("team", {}).get("name", "?")
                games.append({
                    "date": game.get("officialDate", ""),
                    "opponent": opp_name,
                    "score": f"{our_score}-{opp_score}",
                    "win": our_score > opp_score,
                    "home": is_home,
                })
        return games[-count:][::-1] if games else []

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
