"""DaftKings Bot Dashboard — Full operational view: results, P&L, criteria, arbs, run history."""

from __future__ import annotations

import html as html_mod
import os
import sys
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv(override=True)

BOT_ROOT = Path(__file__).resolve().parent
DATA_DIR = BOT_ROOT / "data" / "logs"
BETS_LOG = DATA_DIR / "bets_log.csv"
ARB_LOG = DATA_DIR / "arb_log.csv"
RUN_LOG = DATA_DIR / "run_log.csv"
BOT_LOG = DATA_DIR / "bot.log"

STARTING_BANKROLL = float(os.getenv("STARTING_BANKROLL", "1000"))
LOG_TAIL_LINES = 150  # how many lines from bot.log to show


def read_log_tail(path: Path, max_lines: int = LOG_TAIL_LINES) -> list[dict]:
    """Read the last N lines from bot.log and parse into structured entries."""
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        tail = lines[-max_lines:] if len(lines) > max_lines else lines

        entries: list[dict] = []
        for line in tail:
            line = line.rstrip()
            if not line:
                continue

            # Parse: "2026-04-13 11:24:36,485 INFO main: Running bet settlement..."
            level = "INFO"
            for lvl in ("ERROR", "WARNING", "INFO", "DEBUG"):
                if f" {lvl} " in line:
                    level = lvl
                    break

            # Classify the line into a category for filtering/highlighting
            category = "general"
            line_lower = line.lower()
            if "cycle starting" in line_lower or "cycle complete" in line_lower:
                category = "cycle"
            elif "arb detected" in line_lower:
                category = "arb"
            elif "settled" in line_lower and ("win" in line_lower or "loss" in line_lower or "void" in line_lower or "push" in line_lower):
                category = "settlement"
            elif "bet:" in line_lower and ("logged bet" in line_lower or "placing" in line_lower):
                category = "bet"
            elif "position limit" in line_lower or "kill switch" in line_lower:
                category = "risk"
            elif "haiku" in line_lower and ("tokens" in line_lower or "calling haiku" in line_lower):
                category = "haiku"
            elif level == "ERROR":
                category = "error"
            elif level == "WARNING":
                category = "warning"
            elif "requests remaining" in line_lower:
                category = "api"
            elif line.startswith("===") or line.startswith("{") or line.startswith("}") or line.startswith("  ") or line.startswith("```"):
                category = "raw"  # JSON / banner lines

            entries.append({"line": line, "level": level, "category": category})
        return entries
    except Exception:
        return []


def read_csv_safe(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
        return df if not df.empty else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def _safe_float(val, default: float = 0.0) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_int(val, default: int = 0) -> int:
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _extract_bet_details(row) -> dict:
    """Extract structured bet details from a CSV row.

    Returns dict with: description, odds, book.
    Uses bet_description/bet_odds/bet_book columns if available (new format),
    otherwise parses from haiku_reasoning (historical data).
    """
    import re

    desc = row.get("bet_description", "")
    odds = row.get("bet_odds", "")
    book = row.get("bet_book", "")

    # Clean nan values
    for val_name in ("desc", "odds", "book"):
        val = locals()[val_name]
        if not isinstance(val, str):
            try:
                if val and str(val) != "nan":
                    locals()[val_name] = str(val)
                else:
                    locals()[val_name] = ""
            except (ValueError, TypeError):
                locals()[val_name] = ""
        elif val == "nan":
            locals()[val_name] = ""

    # Re-read after cleanup
    desc = str(desc) if isinstance(desc, str) and desc != "nan" else ""
    try:
        odds = str(int(float(odds))) if odds and str(odds) != "nan" else ""
    except (ValueError, TypeError):
        odds = ""
    book = str(book) if isinstance(book, str) and book != "nan" else ""

    # If we already have structured data, return it
    if desc and odds:
        try:
            odds_int = int(float(odds))
            return {"description": desc, "odds": f"{odds_int:+d}", "book": book}
        except (ValueError, TypeError):
            return {"description": desc, "odds": odds, "book": book}

    # Parse from reasoning for historical data
    reasoning = row.get("haiku_reasoning", "")
    if not isinstance(reasoning, str):
        reasoning = ""
    market = row.get("market_type", "")
    side = str(row.get("recommended_side", "")).lower()
    home = str(row.get("home_team", ""))
    away = str(row.get("away_team", ""))

    # Determine the team we're betting on
    bet_team = home if side == "home" else away if side == "away" else ""
    # Short team name (last word) for display
    short_team = bet_team.split()[-1] if bet_team else side.title()

    parsed_desc = ""
    parsed_odds = ""
    parsed_book = ""

    if market == "spreads":
        # Strategy 1: "TeamName/ShortName +/-N.N at/@ +/-NNN"
        # e.g. "Cincinnati +0.25 at -105", "Buffalo Sabres -1.0 at +102"
        team_names = [bet_team]
        if bet_team:
            team_names.extend([bet_team.split()[-1], bet_team.split()[0]])
        for name in team_names:
            if not name:
                continue
            pat = re.escape(name) + r'\s+([+-]\d+\.?\d*)\s+(?:at|@)\s+([+-]\d+)'
            match = re.search(pat, reasoning, re.IGNORECASE)
            if match:
                parsed_desc = f"{short_team} {match.group(1)}"
                parsed_odds = match.group(2)
                break

        # Strategy 2: "TeamName +/-N.N (+/-NNN)" — odds in parens
        if not parsed_desc:
            for name in team_names:
                if not name:
                    continue
                pat = re.escape(name) + r'\s+([+-]\d+\.?\d*)\s+\(([+-]\d+)\)'
                match = re.search(pat, reasoning, re.IGNORECASE)
                if match:
                    parsed_desc = f"{short_team} {match.group(1)}"
                    parsed_odds = match.group(2)
                    break

        # Strategy 3: "The -17.5 spread at -108" or "-17.5 at -108"
        if not parsed_desc:
            match = re.search(r'(?:the\s+)?([+-]\d+\.?\d*)\s+(?:spread\s+)?at\s+([+-]\d+)', reasoning, re.IGNORECASE)
            if match:
                parsed_desc = f"{short_team} {match.group(1)}"
                parsed_odds = match.group(2)

        # Strategy 4: "at +4.5 (+112)" — "value at" pattern
        if not parsed_desc:
            match = re.search(r'at\s+([+-]\d+\.?\d*)\s+\(([+-]\d+)\)', reasoning, re.IGNORECASE)
            if match:
                parsed_desc = f"{short_team} {match.group(1)}"
                parsed_odds = match.group(2)

        # Strategy 5: "bet Boston -17.5" or "bet TeamName -N.N"
        if not parsed_desc:
            for name in team_names:
                if not name:
                    continue
                pat = r'bet\s+' + re.escape(name) + r'\s+([+-]\d+\.?\d*)'
                match = re.search(pat, reasoning, re.IGNORECASE)
                if match:
                    parsed_desc = f"{short_team} {match.group(1)}"
                    break

        # Strategy 6: Just find any spread number near the team name
        if not parsed_desc:
            for name in team_names:
                if not name:
                    continue
                pat = re.escape(name) + r'.{0,40}?([+-]\d+\.?\d*)'
                match = re.search(pat, reasoning, re.IGNORECASE)
                if match:
                    val = float(match.group(1))
                    # Sanity: spreads are between -50 and +50, odds are outside
                    if -50 <= val <= 50 and abs(val) != 0:
                        parsed_desc = f"{short_team} {match.group(1)}"
                        break

        # Strategy 7: "odds on TeamName +/-N.N" — odds come before the team
        if not parsed_desc:
            match = re.search(r'([+-]\d+)\s+odds\s+on\s+\w[\w\s]*?\s+([+-]\d+\.?\d*)', reasoning, re.IGNORECASE)
            if match:
                parsed_odds = match.group(1)
                parsed_desc = f"{short_team} {match.group(2)}"

        # Strategy 8: "BookName +/-NNN odds" — extract odds from book mention
        if not parsed_odds:
            match = re.search(r'(\w+)\s+([+-]\d{3,})\s+odds', reasoning, re.IGNORECASE)
            if match:
                parsed_odds = match.group(2)
                if not parsed_book:
                    parsed_book = match.group(1).lower()

        # Strategy 9: Find odds separately if we got desc but no odds
        if parsed_desc and not parsed_odds:
            match = re.search(r'(?:at|@)\s+([+-]\d{3,})', reasoning, re.IGNORECASE)
            if match:
                parsed_odds = match.group(1)

    elif market == "h2h":
        team = bet_team or "Draw"
        parsed_desc = f"{team} ML"
        # Find American odds near team name or anywhere
        for name_part in [team, team.split()[-1] if team else ""]:
            if not name_part:
                continue
            match = re.search(
                re.escape(name_part) + r'.{0,40}?([+-]\d{3,})',
                reasoning, re.IGNORECASE,
            )
            if match:
                parsed_odds = match.group(1)
                break

    elif market == "totals":
        # "Over 222.5 at -154" or "Under 6.0 at -105"
        match = re.search(r'((?:Over|Under)\s+\d+\.?\d*)\s+(?:at|@)\s+([+-]\d+)', reasoning, re.IGNORECASE)
        if match:
            parsed_desc = match.group(1)
            parsed_odds = match.group(2)
        else:
            match = re.search(r'((?:Over|Under)\s+\d+\.?\d*)', reasoning, re.IGNORECASE)
            if match:
                parsed_desc = match.group(1)

    elif market == "outrights":
        parsed_desc = "Outright/Future"

    # Fallback description — use sport defaults for known fixed-line markets
    if not parsed_desc and market == "spreads":
        sport = str(row.get("sport", ""))
        # NHL puck line and MLB run line are always +/- 1.5
        default_lines = {"icehockey_nhl": 1.5, "baseball_mlb": 1.5}
        default = default_lines.get(sport)
        if default is not None:
            # Home favorites get -1.5, away underdogs get +1.5
            # But Haiku picks the value side, so sign depends on context
            # Use + for both as the "getting points" read is more common for value
            parsed_desc = f"{short_team} +{default}"
        else:
            parsed_desc = f"{bet_team or side.title()} Spread"
    elif not parsed_desc:
        mkt_labels = {"h2h": "ML", "totals": "Total", "outrights": "Future"}
        parsed_desc = f"{bet_team or side.title()} {mkt_labels.get(market, market)}"

    # Extract book from arb_books column
    arb_books = row.get("arb_books", "")
    if isinstance(arb_books, str) and arb_books not in ("", "nan"):
        parsed_book = arb_books

    return {
        "description": desc or parsed_desc,
        "odds": odds or parsed_odds,
        "book": book or parsed_book,
    }


def _truncate(text: str, max_len: int = 200) -> str:
    if not isinstance(text, str):
        return ""
    return text[:max_len] + "..." if len(text) > max_len else text


def _sport_label(sport: str) -> str:
    """Convert API sport key to a human-readable label."""
    labels = {
        "americanfootball_nfl": "NFL",
        "basketball_nba": "NBA",
        "baseball_mlb": "MLB",
        "icehockey_nhl": "NHL",
        "soccer_epl": "EPL",
        "soccer_usa_mls": "MLS",
        "golf_masters_tournament_winner": "Masters",
        "golf_pga_championship_winner": "PGA",
        "golf_the_open_championship_winner": "The Open",
        "golf_us_open_winner": "US Open",
        "tennis_atp_monte_carlo_masters": "ATP Monte Carlo",
    }
    return labels.get(sport, sport)


def _result_badge(result: str) -> str:
    """Return styled badge HTML for a bet result."""
    r = str(result).strip().lower()
    if r == "win":
        return '<span class="badge badge-win">WIN</span>'
    elif r == "loss":
        return '<span class="badge badge-loss">LOSS</span>'
    elif r == "push":
        return '<span class="badge badge-push">PUSH</span>'
    elif r == "void":
        return '<span class="badge badge-void">VOID</span>'
    elif r == "pass":
        return '<span class="badge badge-pass">PASS</span>'
    else:
        return '<span class="badge badge-pending">PENDING</span>'


def _pnl_cell(pnl: float) -> str:
    if pnl > 0:
        return f'<span class="pnl-pos">+${pnl:.2f}</span>'
    elif pnl < 0:
        return f'<span class="pnl-neg">-${abs(pnl):.2f}</span>'
    return '<span class="pnl-zero">$0.00</span>'


def generate_html() -> str:
    bets = read_csv_safe(BETS_LOG)
    arbs = read_csv_safe(ARB_LOG)
    runs = read_csv_safe(RUN_LOG)

    # ── Classify bets ──────────────────────────────────────────────
    actual_bets = pd.DataFrame()
    settled_bets = pd.DataFrame()
    pending_bets = pd.DataFrame()
    passed_bets = pd.DataFrame()

    if not bets.empty and "result" in bets.columns:
        has_stake = pd.to_numeric(bets["actual_stake_usd"], errors="coerce").fillna(0) > 0
        is_pass = bets["result"].astype(str).str.strip().str.lower() == "pass"

        actual_bets = bets[has_stake].copy()
        passed_bets = bets[is_pass].copy()

        # Settled = has a result that isn't empty/pass
        has_result = actual_bets["result"].astype(str).str.strip().str.lower().isin(
            ["win", "loss", "push", "void"]
        )
        settled_bets = actual_bets[has_result].copy()
        pending_bets = actual_bets[~has_result].copy()

    # ── Summary stats ──────────────────────────────────────────────
    total_bets = len(actual_bets)
    total_settled = len(settled_bets)
    wins = len(settled_bets[settled_bets["result"].astype(str).str.lower() == "win"]) if not settled_bets.empty else 0
    losses = len(settled_bets[settled_bets["result"].astype(str).str.lower() == "loss"]) if not settled_bets.empty else 0
    pushes = len(settled_bets[settled_bets["result"].astype(str).str.lower() == "push"]) if not settled_bets.empty else 0
    pending_count = len(pending_bets)
    total_passes = len(passed_bets)

    win_rate = (wins / total_settled * 100) if total_settled > 0 else 0.0

    total_pnl = 0.0
    total_staked = 0.0
    if not settled_bets.empty:
        total_pnl = pd.to_numeric(settled_bets["pnl_usd"], errors="coerce").fillna(0).sum()
        total_staked = pd.to_numeric(settled_bets["actual_stake_usd"], errors="coerce").fillna(0).sum()

    roi = (total_pnl / total_staked * 100) if total_staked > 0 else 0.0
    bankroll = STARTING_BANKROLL + total_pnl

    total_arbs = len(arbs)
    total_runs = len(runs)

    # API cost
    total_cost = 0.0
    total_tokens = 0
    total_haiku_calls = 0
    if not runs.empty and "api_cost_usd" in runs.columns:
        total_cost = pd.to_numeric(runs["api_cost_usd"], errors="coerce").sum()
        total_tokens = (
            pd.to_numeric(runs.get("input_tokens", 0), errors="coerce").sum()
            + pd.to_numeric(runs.get("output_tokens", 0), errors="coerce").sum()
        )
        total_haiku_calls = pd.to_numeric(runs.get("haiku_calls", 0), errors="coerce").sum()

    # ── Settled Bets table ─────────────────────────────────────────
    settled_html = ""
    if not settled_bets.empty:
        for _, row in settled_bets.iloc[::-1].iterrows():
            result = str(row.get("result", "")).strip().lower()
            sport = _sport_label(row.get("sport", ""))
            home = row.get("home_team", "")
            away = row.get("away_team", "")
            conf = _safe_float(row.get("confidence", 0))
            edge = _safe_float(row.get("estimated_edge", 0))
            impl_prob = _safe_float(row.get("implied_prob", 0))
            true_prob = _safe_float(row.get("estimated_true_prob", 0))
            stake = _safe_float(row.get("actual_stake_usd", 0))
            pnl = _safe_float(row.get("pnl_usd", 0))
            score = row.get("score_summary", "")
            if not isinstance(score, str) or score == "nan":
                score = ""
            reasoning = row.get("haiku_reasoning", "")
            if not isinstance(reasoning, str):
                reasoning = ""
            key_factors = row.get("key_factors", "")
            if not isinstance(key_factors, str) or key_factors == "nan":
                key_factors = ""
            arb_flag = row.get("arb_flag", False)

            # Extract the actual bet details
            bet = _extract_bet_details(row)
            bet_desc = bet["description"]
            bet_odds = bet["odds"]
            bet_book = bet["book"]

            arb_indicator = ' <span class="arb-tag">ARB</span>' if arb_flag else ""
            row_class = "row-win" if result == "win" else "row-loss" if result == "loss" else ""

            # Format odds display
            odds_display = bet_odds if bet_odds else "-"
            try:
                odds_display = f"{int(float(bet_odds)):+d}" if bet_odds else "-"
            except (ValueError, TypeError):
                odds_display = bet_odds or "-"

            # Book display
            book_display = bet_book.replace("_", " ").title() if bet_book else ""

            # Key factors pills
            factors_html = ""
            if key_factors:
                for factor in key_factors.split(" | ")[:5]:
                    factors_html += f'<span class="factor-pill">{html_mod.escape(factor.strip())}</span>'

            settled_html += f"""<tr class="{row_class}">
                <td>{_result_badge(result)}</td>
                <td>{sport}{arb_indicator}</td>
                <td>{away} @ {home}</td>
                <td class="bet-desc"><strong>{html_mod.escape(bet_desc)}</strong></td>
                <td class="bet-odds">{odds_display}</td>
                <td class="bet-book">{book_display}</td>
                <td>${stake:.2f}</td>
                <td>{_pnl_cell(pnl)}</td>
                <td class="score-cell">{score if score else '-'}</td>
            </tr>
            <tr class="detail-row {row_class}">
                <td colspan="9">
                    <div class="criteria-bar">Conf: {conf:.0%} &bull; Edge: {edge:.1%} &bull; True Prob: {true_prob:.1%}{' &bull; Implied: ' + f'{impl_prob:.1%}' if impl_prob > 0 else ''}</div>
                    <div class="factors-row">{factors_html}</div>
                    <div class="reasoning-full">{_truncate(html_mod.escape(reasoning), 350)}</div>
                </td>
            </tr>"""

    # ── Pending Bets table ─────────────────────────────────────────
    pending_html = ""
    if not pending_bets.empty:
        for _, row in pending_bets.iloc[::-1].iterrows():
            sport = _sport_label(row.get("sport", ""))
            home = row.get("home_team", "")
            away = row.get("away_team", "")
            conf = _safe_float(row.get("confidence", 0))
            edge = _safe_float(row.get("estimated_edge", 0))
            true_prob = _safe_float(row.get("estimated_true_prob", 0))
            stake = _safe_float(row.get("actual_stake_usd", 0))
            reasoning = row.get("haiku_reasoning", "")
            if not isinstance(reasoning, str):
                reasoning = ""
            key_factors = row.get("key_factors", "")
            if not isinstance(key_factors, str) or key_factors == "nan":
                key_factors = ""
            arb_flag = row.get("arb_flag", False)
            game_time = str(row.get("game_time", ""))[:16]

            bet = _extract_bet_details(row)
            bet_desc = bet["description"]
            bet_odds = bet["odds"]
            bet_book = bet["book"]

            arb_indicator = ' <span class="arb-tag">ARB</span>' if arb_flag else ""

            odds_display = "-"
            try:
                odds_display = f"{int(float(bet_odds)):+d}" if bet_odds else "-"
            except (ValueError, TypeError):
                odds_display = bet_odds or "-"

            book_display = bet_book.replace("_", " ").title() if bet_book else ""

            factors_html = ""
            if key_factors:
                for factor in key_factors.split(" | ")[:5]:
                    factors_html += f'<span class="factor-pill">{html_mod.escape(factor.strip())}</span>'

            pending_html += f"""<tr>
                <td>{sport}{arb_indicator}</td>
                <td>{away} @ {home}</td>
                <td class="game-time">{game_time}</td>
                <td class="bet-desc"><strong>{html_mod.escape(bet_desc)}</strong></td>
                <td class="bet-odds">{odds_display}</td>
                <td class="bet-book">{book_display}</td>
                <td>${stake:.2f}</td>
            </tr>
            <tr class="detail-row">
                <td colspan="7">
                    <div class="criteria-bar">Conf: {conf:.0%} &bull; Edge: {edge:.1%} &bull; True Prob: {true_prob:.1%}</div>
                    <div class="factors-row">{factors_html}</div>
                    <div class="reasoning-full">{_truncate(html_mod.escape(reasoning), 350)}</div>
                </td>
            </tr>"""

    # ── Passed table (last 20) ─────────────────────────────────────
    passed_html = ""
    if not passed_bets.empty:
        for _, row in passed_bets.iloc[::-1].head(20).iterrows():
            sport = _sport_label(row.get("sport", ""))
            home = row.get("home_team", "")
            away = row.get("away_team", "")
            mkt = row.get("market_type", "")
            conf = _safe_float(row.get("confidence", 0))
            edge = _safe_float(row.get("estimated_edge", 0))
            reasoning = row.get("haiku_reasoning", "")
            if isinstance(reasoning, str) and reasoning.startswith("PASS: "):
                reasoning = reasoning[6:]
            if not isinstance(reasoning, str):
                reasoning = ""

            passed_html += f"""<tr>
                <td>{sport}</td>
                <td>{away} @ {home}</td>
                <td>{mkt}</td>
                <td>{conf:.0%}</td>
                <td>{edge:.1%}</td>
                <td class="reasoning">{_truncate(reasoning, 180)}</td>
            </tr>"""

    # ── Arbs table (top 15) ────────────────────────────────────────
    arbs_html = ""
    if not arbs.empty:
        arbs_sorted = arbs.sort_values("arb_profit_pct", ascending=False).head(15)
        for _, row in arbs_sorted.iterrows():
            sport = _sport_label(row.get("sport", ""))
            home = row.get("home_team", "")
            away = row.get("away_team", "")
            side = row.get("mispriced_side", "")
            book = row.get("better_book", "")
            odds = row.get("better_odds", "")
            margin = _safe_float(row.get("arb_profit_pct", 0))
            odds_val = _safe_int(odds)

            heat = "hot" if margin > 40 else "warm" if margin > 20 else ""
            arbs_html += f"""<tr class="{heat}">
                <td>{sport}</td>
                <td>{away} @ {home}</td>
                <td><strong>{side}</strong></td>
                <td>{book}</td>
                <td>{odds_val:+d}</td>
                <td class="margin">{margin:.1f}%</td>
            </tr>"""

    # ── Runs table (last 10) ───────────────────────────────────────
    runs_html = ""
    if not runs.empty:
        for _, row in runs.iloc[::-1].head(10).iterrows():
            ts = str(row.get("timestamp", ""))[:19]
            mkts = row.get("markets_scanned", 0)
            arb_count = row.get("arbs_found", 0)
            analyzed = row.get("opportunities_analyzed", 0)
            placed = row.get("bets_placed", 0)
            dur = _safe_float(row.get("duration_seconds", 0))
            errs = _safe_int(row.get("errors", 0))
            cost = _safe_float(row.get("api_cost_usd", 0))
            calls = _safe_int(row.get("haiku_calls", 0))
            runs_html += f"""<tr>
                <td>{ts}</td>
                <td>{mkts}</td>
                <td>{arb_count}</td>
                <td>{analyzed}</td>
                <td>{placed}</td>
                <td>{dur:.0f}s</td>
                <td>{'$' + f'{cost:.4f}' if cost > 0 else '-'}</td>
                <td>{calls}</td>
                <td>{'<span class="status-err">ERR</span>' if errs > 0 else '<span class="status-ok">OK</span>'}</td>
            </tr>"""

    # ── Bot Log (last N lines) ───────────────────────────────────
    log_entries = read_log_tail(BOT_LOG)
    log_html = ""
    error_count = 0
    warning_count = 0
    for entry in log_entries:
        line = entry["line"]
        cat = entry["category"]
        lvl = entry["level"]

        if lvl == "ERROR":
            error_count += 1
        elif lvl == "WARNING":
            warning_count += 1

        safe_line = html_mod.escape(line)

        css_class = f"log-{cat}"
        if lvl == "ERROR":
            css_class += " log-error"
        elif lvl == "WARNING":
            css_class += " log-warn"

        log_html += f'<div class="log-line {css_class}">{safe_line}</div>\n'

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    paper_mode = os.getenv("PAPER_MODE", "true")

    # ── P&L color ──────────────────────────────────────────────────
    pnl_color = "#00d4aa" if total_pnl >= 0 else "#ff4444"
    roi_color = "#00d4aa" if roi >= 0 else "#ff4444"
    bankroll_color = "#00d4aa" if bankroll >= STARTING_BANKROLL else "#ff4444"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="30">
<title>DaftKings Dashboard</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
        background: #0a0e17;
        color: #e0e6ed;
        padding: 20px;
        min-width: 1200px;
    }}

    /* Header */
    .header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;
        padding-bottom: 16px;
        border-bottom: 1px solid #1e2a3a;
    }}
    .header h1 {{
        font-size: 28px;
        color: #00d4aa;
        letter-spacing: 2px;
    }}
    .header .mode {{
        background: {'#1a3a1a' if paper_mode == 'true' else '#3a1a1a'};
        color: {'#00ff88' if paper_mode == 'true' else '#ff4444'};
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 14px;
    }}
    .header .refresh {{ color: #556; font-size: 12px; }}

    /* Stats Grid */
    .stats-grid {{
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 12px;
        margin-bottom: 24px;
    }}
    .stat-card {{
        background: #111827;
        border: 1px solid #1e2a3a;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }}
    .stat-card .value {{
        font-size: 28px;
        font-weight: 700;
        color: #00d4aa;
    }}
    .stat-card .label {{
        color: #6b7b8d;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 4px;
    }}
    .stat-card.highlight .value {{ color: {pnl_color}; }}
    .stat-card.roi .value {{ color: {roi_color}; }}
    .stat-card.bankroll .value {{ color: {bankroll_color}; }}
    .stat-card.cost .value {{ color: #fbbf24; font-size: 22px; }}
    .stat-card.win .value {{ color: #00d4aa; }}
    .stat-card.loss .value {{ color: #ff4444; }}

    /* Sections */
    .section {{
        background: #111827;
        border: 1px solid #1e2a3a;
        border-radius: 10px;
        margin-bottom: 20px;
        overflow: hidden;
    }}
    .section h2 {{
        padding: 14px 20px;
        font-size: 15px;
        color: #8899aa;
        border-bottom: 1px solid #1e2a3a;
        text-transform: uppercase;
        letter-spacing: 1px;
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    .section h2 .count {{
        background: #00d4aa22;
        color: #00d4aa;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 700;
    }}

    /* Tables */
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th {{
        text-align: left;
        padding: 10px 14px;
        color: #556677;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1px;
        border-bottom: 1px solid #1e2a3a;
        position: sticky;
        top: 0;
        background: #111827;
    }}
    td {{ padding: 10px 14px; border-bottom: 1px solid #0d1520; }}
    tr:hover {{ background: #151f2e; }}

    /* Badges */
    .badge {{ padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; display: inline-block; }}
    .badge-win {{ background: #00d4aa22; color: #00d4aa; }}
    .badge-loss {{ background: #ff444422; color: #ff4444; }}
    .badge-push {{ background: #fbbf2422; color: #fbbf24; }}
    .badge-void {{ background: #55667722; color: #778899; }}
    .badge-pass {{ background: #55667722; color: #778899; }}
    .badge-pending {{ background: #3b82f622; color: #60a5fa; }}
    .arb-tag {{
        background: #fbbf2422;
        color: #fbbf24;
        padding: 2px 6px;
        border-radius: 8px;
        font-size: 10px;
        font-weight: 700;
        margin-left: 4px;
    }}

    /* Row highlighting */
    .row-win {{ background: #00d4aa06; }}
    .row-loss {{ background: #ff444406; }}

    /* P&L */
    .pnl-pos {{ color: #00d4aa; font-weight: 700; }}
    .pnl-neg {{ color: #ff4444; font-weight: 700; }}
    .pnl-zero {{ color: #556677; }}

    /* Detail rows */
    .detail-row td {{
        padding: 6px 14px 12px;
        border-bottom: 2px solid #1e2a3a;
    }}
    .detail-row:hover {{ background: transparent; }}
    .criteria-bar {{
        color: #8899aa;
        font-size: 12px;
        margin-bottom: 4px;
    }}
    .factors-row {{
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        margin-bottom: 4px;
    }}
    .factor-pill {{
        background: #1e2a3a;
        color: #aabbcc;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 11px;
    }}
    .reasoning-full {{
        color: #667788;
        font-size: 12px;
        line-height: 1.5;
        max-width: 100%;
    }}

    /* Bet description */
    .bet-desc {{ color: #e0e6ed; font-size: 13px; white-space: nowrap; }}
    .bet-odds {{ color: #fbbf24; font-weight: 700; font-size: 14px; white-space: nowrap; }}
    .bet-book {{ color: #8899aa; font-size: 12px; white-space: nowrap; }}

    /* Score */
    .score-cell {{ color: #aabbcc; font-weight: 600; white-space: nowrap; }}

    /* Game time */
    .game-time {{ color: #60a5fa; font-size: 12px; white-space: nowrap; }}

    /* Arb heat */
    .hot {{ background: #ff444410; }}
    .warm {{ background: #fbbf2408; }}
    .margin {{ color: #fbbf24; font-weight: 700; }}
    .hot .margin {{ color: #ff6b6b; }}

    /* Reasoning in pass table */
    .reasoning {{ color: #667788; font-size: 12px; max-width: 450px; line-height: 1.4; }}

    /* Status */
    .status-ok {{ color: #00d4aa; font-weight: 600; }}
    .status-err {{ color: #ff4444; font-weight: 600; }}

    /* Empty state */
    .empty {{ text-align: center; color: #334455; padding: 20px; }}

    /* Bot Log Viewer */
    .log-viewer {{
        background: #0d1117;
        padding: 12px 16px;
        font-family: 'Consolas', 'Fira Code', 'Cascadia Code', monospace;
        font-size: 12px;
        line-height: 1.6;
        max-height: 500px;
        overflow-y: auto;
        overflow-x: auto;
        white-space: pre;
    }}
    .log-line {{ color: #8b949e; }}
    .log-line.log-error {{ color: #ff4444; font-weight: 600; }}
    .log-line.log-warn {{ color: #fbbf24; }}
    .log-cycle {{ color: #00d4aa; font-weight: 700; }}
    .log-settlement {{ color: #60a5fa; font-weight: 600; }}
    .log-bet {{ color: #00d4aa; }}
    .log-arb {{ color: #fbbf24; }}
    .log-risk {{ color: #f97316; }}
    .log-haiku {{ color: #a78bfa; }}
    .log-api {{ color: #6b7b8d; }}
    .log-raw {{ color: #556677; font-size: 11px; }}
    .log-general {{ color: #8b949e; }}

    /* Log filter buttons */
    .log-filters {{
        padding: 10px 20px;
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        border-bottom: 1px solid #1e2a3a;
    }}
    .log-filter-btn {{
        background: #1e2a3a;
        color: #8899aa;
        border: 1px solid #2d3b4d;
        padding: 4px 12px;
        border-radius: 14px;
        font-size: 11px;
        cursor: pointer;
        font-family: inherit;
    }}
    .log-filter-btn:hover {{ background: #2d3b4d; color: #e0e6ed; }}
    .log-filter-btn.active {{ background: #00d4aa22; color: #00d4aa; border-color: #00d4aa44; }}
    .log-summary {{
        color: #6b7b8d;
        font-size: 12px;
        margin-left: auto;
        display: flex;
        gap: 12px;
        align-items: center;
    }}
    .log-summary .err-count {{ color: #ff4444; font-weight: 600; }}
    .log-summary .warn-count {{ color: #fbbf24; font-weight: 600; }}

    /* Two-column layout for bottom sections */
    .two-col {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 20px;
        margin-bottom: 20px;
    }}
    .two-col .section {{ margin-bottom: 0; }}
</style>
</head>
<body>

<!-- Header -->
<div class="header">
    <h1>DAFTKINGS</h1>
    <div>
        <span class="mode">{'PAPER MODE' if paper_mode == 'true' else 'LIVE TRADING'}</span>
        <span class="refresh">&nbsp; Updated {now} &bull; auto-refreshes 30s</span>
    </div>
</div>

<!-- Summary Stats -->
<div class="stats-grid">
    <div class="stat-card">
        <div class="value">{total_bets}</div>
        <div class="label">Bets Placed</div>
    </div>
    <div class="stat-card win">
        <div class="value">{wins}W - {losses}L - {pushes}P</div>
        <div class="label">Record ({total_settled} settled)</div>
    </div>
    <div class="stat-card">
        <div class="value">{win_rate:.0f}%</div>
        <div class="label">Win Rate</div>
    </div>
    <div class="stat-card highlight">
        <div class="value">{'+'if total_pnl>=0 else ''}${total_pnl:.2f}</div>
        <div class="label">Total P&L</div>
    </div>
    <div class="stat-card roi">
        <div class="value">{'+'if roi>=0 else ''}{roi:.1f}%</div>
        <div class="label">ROI</div>
    </div>
    <div class="stat-card bankroll">
        <div class="value">${bankroll:.2f}</div>
        <div class="label">Bankroll</div>
    </div>
    <div class="stat-card">
        <div class="value">{pending_count}</div>
        <div class="label">Pending</div>
    </div>
    <div class="stat-card">
        <div class="value">{total_passes}</div>
        <div class="label">Passes</div>
    </div>
    <div class="stat-card">
        <div class="value">{total_arbs}</div>
        <div class="label">Arbs Found</div>
    </div>
    <div class="stat-card cost">
        <div class="value">${total_cost:.4f}</div>
        <div class="label">API Cost &bull; {int(total_haiku_calls)} calls &bull; {int(total_tokens):,} tok</div>
    </div>
</div>

<!-- Settled Bets -->
<div class="section">
    <h2>Settled Bets <span class="count">{total_settled}</span></h2>
    <table>
        <thead><tr>
            <th>Result</th><th>Sport</th><th>Match</th><th>Bet</th>
            <th>Odds</th><th>Book</th><th>Stake</th><th>P&L</th><th>Score</th>
        </tr></thead>
        <tbody>{settled_html if settled_html else '<tr><td colspan="9" class="empty">No settled bets yet &mdash; results appear after games complete</td></tr>'}</tbody>
    </table>
</div>

<!-- Pending Bets -->
<div class="section">
    <h2>Pending Bets <span class="count">{pending_count}</span></h2>
    <table>
        <thead><tr>
            <th>Sport</th><th>Match</th><th>Game Time</th><th>Bet</th>
            <th>Odds</th><th>Book</th><th>Stake</th>
        </tr></thead>
        <tbody>{pending_html if pending_html else '<tr><td colspan="7" class="empty">No pending bets</td></tr>'}</tbody>
    </table>
</div>

<!-- Two-column: Arbs + Run History -->
<div class="two-col">
    <div class="section">
        <h2>Top Arbitrage Signals <span class="count">{total_arbs}</span></h2>
        <div style="max-height:400px;overflow-y:auto;">
        <table>
            <thead><tr><th>Sport</th><th>Match</th><th>Value Side</th><th>Book</th><th>Odds</th><th>Margin</th></tr></thead>
            <tbody>{arbs_html if arbs_html else '<tr><td colspan="6" class="empty">No arbs detected</td></tr>'}</tbody>
        </table>
        </div>
    </div>
    <div class="section">
        <h2>Run History <span class="count">{total_runs}</span></h2>
        <div style="max-height:400px;overflow-y:auto;">
        <table>
            <thead><tr><th>Time</th><th>Mkts</th><th>Arbs</th><th>Analyzed</th><th>Bets</th><th>Dur</th><th>Cost</th><th>Haiku</th><th>Status</th></tr></thead>
            <tbody>{runs_html if runs_html else '<tr><td colspan="9" class="empty">No runs yet</td></tr>'}</tbody>
        </table>
        </div>
    </div>
</div>

<!-- Passed Opportunities -->
<div class="section">
    <h2>Passed Opportunities (last 20) <span class="count">{total_passes}</span></h2>
    <div style="max-height:500px;overflow-y:auto;">
    <table>
        <thead><tr><th>Sport</th><th>Match</th><th>Market</th><th>Conf</th><th>Edge</th><th>Why Passed</th></tr></thead>
        <tbody>{passed_html if passed_html else '<tr><td colspan="6" class="empty">No passes yet</td></tr>'}</tbody>
    </table>
    </div>
</div>

<!-- Bot Log -->
<div class="section">
    <h2>Bot Log (last {LOG_TAIL_LINES} lines)</h2>
    <div class="log-filters">
        <button class="log-filter-btn active" onclick="filterLog('all')">All</button>
        <button class="log-filter-btn" onclick="filterLog('cycle')">Cycles</button>
        <button class="log-filter-btn" onclick="filterLog('bet')">Bets</button>
        <button class="log-filter-btn" onclick="filterLog('settlement')">Settlements</button>
        <button class="log-filter-btn" onclick="filterLog('arb')">Arbs</button>
        <button class="log-filter-btn" onclick="filterLog('risk')">Risk</button>
        <button class="log-filter-btn" onclick="filterLog('haiku')">Haiku</button>
        <button class="log-filter-btn" onclick="filterLog('error')">Errors</button>
        <button class="log-filter-btn" onclick="filterLog('warning')">Warnings</button>
        <div class="log-summary">
            <span>{len(log_entries)} lines</span>
            {'<span class="err-count">' + str(error_count) + ' errors</span>' if error_count > 0 else ''}
            {'<span class="warn-count">' + str(warning_count) + ' warnings</span>' if warning_count > 0 else ''}
        </div>
    </div>
    <div class="log-viewer" id="logViewer">
{log_html if log_html else '<div class="log-line" style="color:#334455">No log entries yet</div>'}
    </div>
</div>

<script>
function filterLog(category) {{
    const viewer = document.getElementById('logViewer');
    const lines = viewer.querySelectorAll('.log-line');
    const buttons = document.querySelectorAll('.log-filter-btn');

    buttons.forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');

    lines.forEach(line => {{
        if (category === 'all') {{
            line.style.display = '';
        }} else {{
            const hasCategory = line.classList.contains('log-' + category);
            line.style.display = hasCategory ? '' : 'none';
        }}
    }});

    // Scroll to bottom
    viewer.scrollTop = viewer.scrollHeight;
}}

// Auto-scroll log to bottom on load
document.addEventListener('DOMContentLoaded', function() {{
    const viewer = document.getElementById('logViewer');
    if (viewer) viewer.scrollTop = viewer.scrollHeight;
}});
</script>

</body>
</html>"""


class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        html = generate_html()
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        pass  # Suppress console logs


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8888
    server = HTTPServer(("127.0.0.1", port), DashboardHandler)
    print(f"DaftKings Dashboard running at http://localhost:{port}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped")
        server.server_close()


if __name__ == "__main__":
    main()
