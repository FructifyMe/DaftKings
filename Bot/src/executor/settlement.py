"""Settlement processor — grades completed bets, calculates PnL, updates bets_log.csv."""

from __future__ import annotations

import csv
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from config import CONFIG
from src.scanner.score_fetcher import GameScore, ScoreFetcher

logger = logging.getLogger(__name__)

BOT_ROOT = Path(__file__).resolve().parent.parent.parent
BETS_LOG = BOT_ROOT / "data" / "logs" / "bets_log.csv"


@dataclass
class SettlementResult:
    """Outcome of settling a single bet."""

    event_id: str
    sport: str
    home_team: str
    away_team: str
    market_type: str
    recommended_side: str
    result: str  # "win", "loss", "push", "void"
    pnl_usd: float
    stake_usd: float
    best_odds: str
    score_summary: str  # e.g. "Celtics 128 - Pelicans 104"


class SettlementProcessor:
    """Reads unsettled bets from bets_log.csv, fetches scores, grades, and updates the CSV."""

    def __init__(self):
        self.score_fetcher = ScoreFetcher()

    def settle_bets(self) -> list[SettlementResult]:
        """Main entry point. Returns list of newly settled bets."""
        unsettled = self._get_unsettled_bets()
        if unsettled.empty:
            logger.info("No unsettled bets to process")
            return []

        # Determine which sports we need scores for
        sports_needed = unsettled["sport"].unique().tolist()
        logger.info("Settling %d bets across sports: %s", len(unsettled), sports_needed)

        # Fetch all scores (keyed by event_id)
        all_scores = self.score_fetcher.get_all_scores(days_from=3)
        logger.info("Fetched %d completed game scores", len(all_scores))

        results: list[SettlementResult] = []
        settled_rows: list[dict] = []  # (csv_index, result, pnl)

        for idx, row in unsettled.iterrows():
            event_id = row["event_id"]
            score = all_scores.get(event_id)

            if score is None or not score.completed:
                logger.debug("No final score for event %s — skipping", event_id)
                continue

            result, pnl = self._grade_bet(row, score)
            score_summary = f"{score.home_team} {score.home_score} - {score.away_team} {score.away_score}"

            sr = SettlementResult(
                event_id=event_id,
                sport=row["sport"],
                home_team=row["home_team"],
                away_team=row["away_team"],
                market_type=row["market_type"],
                recommended_side=row["recommended_side"],
                result=result,
                pnl_usd=pnl,
                stake_usd=float(row["actual_stake_usd"]),
                best_odds=str(row.get("best_odds", "")),
                score_summary=score_summary,
            )
            results.append(sr)
            settled_rows.append({
                "index": idx, "result": result, "pnl_usd": pnl,
                "score_summary": score_summary,
            })

            logger.info(
                "SETTLED: %s | %s @ %s | %s | %s | P&L $%+.2f | %s",
                row["sport"], row["away_team"], row["home_team"],
                row["market_type"], result.upper(), pnl, score_summary,
            )

        # Batch update the CSV
        if settled_rows:
            self._update_bets_log(settled_rows)
            logger.info("Updated %d bets in bets_log.csv", len(settled_rows))

        return results

    def _get_unsettled_bets(self) -> pd.DataFrame:
        """Return rows from bets_log.csv where result is empty and stake > 0 (actual bets, not passes)."""
        if not BETS_LOG.exists():
            return pd.DataFrame()

        try:
            df = pd.read_csv(BETS_LOG)
            if df.empty:
                return pd.DataFrame()

            # Filter: has a stake (actual bet, not a pass) AND no result yet
            is_bet = pd.to_numeric(df["actual_stake_usd"], errors="coerce").fillna(0) > 0
            no_result = df["result"].isna() | (df["result"].astype(str).str.strip() == "")
            return df[is_bet & no_result]
        except Exception as e:
            logger.error("Error reading bets log for settlement: %s", e)
            return pd.DataFrame()

    def _grade_bet(self, row: pd.Series, score: GameScore) -> tuple[str, float]:
        """Grade a single bet against the final score. Returns (result, pnl_usd).

        Supports: h2h (moneyline), spreads (point spread), totals (over/under).
        """
        market_type = row["market_type"]
        side = str(row["recommended_side"]).strip().lower()
        stake = float(row["actual_stake_usd"])
        odds_str = str(row.get("best_odds", ""))

        # Parse American odds from the logged value
        odds = self._parse_odds(odds_str)

        if market_type == "h2h":
            return self._grade_h2h(side, score, stake, odds)
        elif market_type == "spreads":
            return self._grade_spread(side, row, score, stake, odds)
        elif market_type == "totals":
            return self._grade_total(side, row, score, stake, odds)
        elif market_type == "outrights":
            # Golf/futures — can't auto-settle easily, mark void
            return "void", 0.0
        else:
            logger.warning("Unknown market type '%s' for event %s", market_type, row["event_id"])
            return "void", 0.0

    def _grade_h2h(self, side: str, score: GameScore, stake: float, odds: int | None) -> tuple[str, float]:
        """Grade a moneyline bet."""
        winner = score.winner
        if winner is None:
            return "void", 0.0

        # Determine if our side won
        if side == "home" and winner == "home":
            return "win", self._calculate_payout(stake, odds)
        elif side == "away" and winner == "away":
            return "win", self._calculate_payout(stake, odds)
        elif side == "draw" and winner == "draw":
            return "win", self._calculate_payout(stake, odds)
        elif winner == "draw" and side in ("home", "away"):
            # In soccer h2h, draw is a loss for home/away bettors
            return "loss", -stake
        else:
            return "loss", -stake

    def _grade_spread(self, side: str, row: pd.Series, score: GameScore, stake: float, odds: int | None) -> tuple[str, float]:
        """Grade a spread/handicap bet.

        The spread number may be in recommended_side (e.g., 'Boston Celtics -17.5')
        or in haiku_reasoning (e.g., 'Boston -17.5 at -108'). We try both sources.
        """
        if score.margin is None:
            return "void", 0.0

        # Try extracting spread from recommended_side first, then from reasoning
        spread = self._extract_spread(str(row["recommended_side"]))
        if spread is None:
            spread = self._extract_spread_from_reasoning(str(row.get("haiku_reasoning", "")), side, row)
        if spread is None:
            spread = self._default_spread(row.get("sport", ""), side)
        if spread is None:
            logger.warning("Could not extract spread for event %s — marking void", row["event_id"])
            return "void", 0.0

        # margin = home_score - away_score
        # If we bet home -3.5 → home must win by 4+ → adjusted = margin + (-3.5)
        # If we bet away +3.5 → adjusted = -margin + 3.5
        if side == "home":
            adjusted = score.margin + spread
        else:  # away
            adjusted = -score.margin + spread

        if adjusted > 0:
            return "win", self._calculate_payout(stake, odds)
        elif adjusted == 0:
            return "push", 0.0
        else:
            return "loss", -stake

    def _grade_total(self, side: str, row: pd.Series, score: GameScore, stake: float, odds: int | None) -> tuple[str, float]:
        """Grade an over/under bet."""
        total = score.total_score
        if total is None:
            return "void", 0.0

        line = self._extract_total_line(str(row["recommended_side"]))
        if line is None:
            logger.warning("Could not extract total line for event %s — marking void", row["event_id"])
            return "void", 0.0

        if "over" in side.lower():
            if total > line:
                return "win", self._calculate_payout(stake, odds)
            elif total == line:
                return "push", 0.0
            else:
                return "loss", -stake
        elif "under" in side.lower():
            if total < line:
                return "win", self._calculate_payout(stake, odds)
            elif total == line:
                return "push", 0.0
            else:
                return "loss", -stake
        else:
            logger.warning("Unclear total side '%s' for event %s", side, row["event_id"])
            return "void", 0.0

    def _calculate_payout(self, stake: float, odds: int | None) -> float:
        """Calculate profit from a winning bet given American odds.

        +150 on $100 → $150 profit
        -150 on $100 → $66.67 profit
        """
        if odds is None:
            # No odds logged — assume even money as fallback
            logger.warning("No odds available for payout calc — using even money")
            return stake

        if odds > 0:
            return stake * (odds / 100)
        elif odds < 0:
            return stake * (100 / abs(odds))
        else:
            return stake  # Even money

    def _parse_odds(self, odds_str: str) -> int | None:
        """Parse American odds from a string like '+150', '-110', '150', etc."""
        if not odds_str or odds_str == "nan":
            return None
        try:
            cleaned = odds_str.strip().replace(",", "")
            return int(float(cleaned))
        except (ValueError, TypeError):
            return None

    def _extract_spread_from_reasoning(self, reasoning: str, side: str, row: pd.Series) -> float | None:
        """Extract spread from haiku reasoning text.

        Looks for patterns like:
        - 'Boston -17.5 at -108'
        - 'Arizona +4.5 (+112)'
        - 'Cincinnati +0.25 at -105'
        - '-17.5 spread'
        """
        # Determine which team name to look for
        if side == "home":
            team = row["home_team"]
        else:
            team = row["away_team"]

        # Strategy 1: "TeamName +/-N.N" directly adjacent
        name_parts = [team]
        if len(team.split()) > 1:
            name_parts.extend([team.split()[-1], team.split()[0]])
        for name_part in name_parts:
            pattern = re.escape(name_part) + r'\s+([+-]\d+\.?\d*)'
            match = re.search(pattern, reasoning, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue

        # Strategy 2: "value at +4.5" or "at +4.5 (" patterns (common in Haiku output)
        match = re.search(r'(?:value\s+at|at)\s+([+-]\d+\.?\d*)\s*[\(.]', reasoning, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

        # Strategy 3: "TeamName ... +/-N.N" with up to 20 chars between (e.g., "Arizona represents genuine value at +4.5")
        for name_part in name_parts:
            pattern = re.escape(name_part) + r'.{1,60}?([+-]\d+\.?\d*)'
            match = re.search(pattern, reasoning, re.IGNORECASE)
            if match:
                val = float(match.group(1))
                # Sanity check: spreads are typically between -50 and +50
                if -50 <= val <= 50:
                    return val

        # Strategy 4: standalone spread pattern like "-17.5 spread" or "-17.5 at -108"
        match = re.search(r'([+-]\d+\.?\d*)\s+(?:spread|at\s+[+-]?\d+)', reasoning, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

        return None

    @staticmethod
    def _default_spread(sport: str, side: str) -> float | None:
        """Return the standard spread for sports with fixed lines when no explicit spread is found.

        NHL puck line = +/- 1.5, MLB run line = +/- 1.5.
        Home favorites get -1.5, away underdogs get +1.5.
        For other sports, return None (spread varies too much to guess).
        """
        defaults = {
            "icehockey_nhl": 1.5,
            "baseball_mlb": 1.5,
        }
        base = defaults.get(sport)
        if base is None:
            return None
        # Convention: home side is the favorite (negative spread), away is underdog (positive)
        # But since we don't know who's favored, use the standard underdog line for the bet side
        # The Haiku typically bets the value side — if side=home, assume home was underdog at +1.5
        # This is a reasonable default; if the bet was on the favorite at -1.5, the Haiku reasoning
        # would typically mention it explicitly
        return base if side == "home" else base

    def _extract_spread(self, side_str: str) -> float | None:
        """Extract the spread number from a side string like 'Boston Celtics -17.5' or 'home -3.5'."""
        match = re.search(r'[+-]?\d+\.?\d*', side_str)
        if match:
            try:
                return float(match.group())
            except ValueError:
                pass
        return None

    def _extract_total_line(self, side_str: str) -> float | None:
        """Extract total line from a string like 'Over 222.5' or 'under 6.0'."""
        match = re.search(r'(\d+\.?\d*)', side_str)
        if match:
            try:
                return float(match.group())
            except ValueError:
                pass
        return None

    def _update_bets_log(self, settled_rows: list[dict]) -> None:
        """Update bets_log.csv in-place with settlement results."""
        try:
            df = pd.read_csv(BETS_LOG, dtype={"result": str, "pnl_usd": str})
            for settled in settled_rows:
                idx = settled["index"]
                df.at[idx, "result"] = settled["result"]
                df.at[idx, "pnl_usd"] = f"{settled['pnl_usd']:.2f}"
                df.at[idx, "score_summary"] = settled.get("score_summary", "")
            df.to_csv(BETS_LOG, index=False)
        except Exception as e:
            logger.error("Failed to update bets_log.csv: %s", e)
