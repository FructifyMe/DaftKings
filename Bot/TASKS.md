# DaftKings Bot — Build Tasks for Claude Code (Opus)
**Read CLAUDE.md, PRD.md, and ARCHITECTURE.md before starting any task.**

These tasks are ordered. Complete each one fully before moving to the next.
Each task includes the exact files to create/edit and the acceptance criteria.

---

## PHASE 0 — PROJECT SETUP

### TASK-001: Initialize Python project
**Files to create:**
- `requirements.txt`
- `.env.example`
- `.gitignore`
- `config.py`

**requirements.txt must include:**
```
anthropic>=0.40.0
requests>=2.31.0
python-dotenv>=1.0.0
pandas>=2.0.0
pytest>=7.4.0
pytest-mock>=3.12.0
```

**Acceptance criteria:**
- `pip install -r requirements.txt` completes with no errors
- `config.py` loads all env vars from `.env` with sensible defaults
- `.gitignore` includes `.env`, `data/logs/*.csv`, `__pycache__/`, `*.pyc`

---

### TASK-002: Create data models
**File to create:** `src/models.py`

**What to build:**
All dataclasses from ARCHITECTURE.md:
- `MarketOdds`
- `BettingOpportunity`
- `ArbResult`
- `AnalysisResult`
- `BetOrder`
- `BetResult`
- `DailyStats`

**Acceptance criteria:**
- All dataclasses importable from `src.models`
- Type hints on all fields
- `__repr__` on each for clean logging

---

## PHASE 1 — SCANNER

### TASK-003: Build OddsFetcher
**File to create:** `src/scanner/odds_fetcher.py`

**What to build:**
Full `OddsFetcher` class per ARCHITECTURE.md spec.

Key behaviors:
- `get_odds(sport, markets)` → calls The Odds API, returns list of `MarketOdds`
- `get_all_sports()` → iterates `CONFIG.active_sports`, returns combined list
- `calculate_implied_prob(american_odds)` → correct formula for + and - odds
- All API calls use `api_call_with_retry` wrapper (3 retries, exponential backoff)
- Log remaining API credits (The Odds API returns `X-Requests-Remaining` header)
- Store raw JSON response to `data/historical/{sport}_{date}.json`

**The Odds API endpoint:**
```
GET https://api.the-odds-api.com/v4/sports/{sport}/odds
params: apiKey, regions=us, markets=h2h,spreads,totals, oddsFormat=american
bookmakers: draftkings,fanduel,betmgm,caesars,pointsbet,bet365
```

**Acceptance criteria:**
- Returns correctly typed `list[MarketOdds]`
- Handles API errors gracefully (returns empty list, logs error)
- `calculate_implied_prob` unit test passes for: -110 → 0.5238, +130 → 0.4348

---

### TASK-004: Build ArbDetector
**File to create:** `src/scanner/arb_detector.py`

**What to build:**
Full `ArbDetector` class per ARCHITECTURE.md spec.

Key behaviors:
- `detect(market)` → returns `ArbResult` if `sum(implied_probs) < ARB_THRESHOLD (0.98)`, else `None`
- `identify_mispriced_side(market)` → returns side + book with the "too good" price (value bet side)
- Calculate arb profit % = `(1 - sum_implied_probs) × 100`

**Acceptance criteria:**
- Unit test: two books pricing +105/-105 each → no arb detected
- Unit test: Book A has +115, Book B has +110 on opposite sides → arb detected, correct side flagged
- Returns `None` cleanly when no arb

---

### TASK-005: Build KalshiClient (market data only)
**File to create:** `src/scanner/kalshi_client.py`

**What to build:**
Kalshi API client for fetching market data (not execution — that's TASK-010).

- `get_markets(sport_category)` → returns list of open Kalshi markets for a sport
- `get_market_price(market_id)` → current yes/no price for a specific contract
- Authentication: API key header per Kalshi docs
- Use sandbox URL in all environments until `PAPER_MODE=false` explicitly set
  - Sandbox: `https://demo-api.kalshi.co/trade-api/v2`
  - Live: `https://trading-api.kalshi.com/trade-api/v2`

**Acceptance criteria:**
- Connects to Kalshi sandbox, returns markets without errors
- Handles auth failure gracefully with clear error message

---

## PHASE 2 — ANALYZER

### TASK-006: Build SituationalAnalyzer
**File to create:** `src/analyzer/situational.py`

**What to build:**
`SituationalAnalyzer` class that enriches a `MarketOdds` object with contextual factors.

For each game, calculate/lookup:
- `home_rest_days`: days since home team's last game (use schedule from The Odds API or hardcode lookup)
- `away_rest_days`: same for away team
- `is_b2b`: True if either team played yesterday
- `weather`: For NFL/MLB, fetch from Open-Meteo free API (`api.open-meteo.com`) using venue coordinates. Return: temp_f, wind_mph, precipitation_pct. Return None for indoor sports.
- `home_advantage`: Configured per sport (NFL: 3 pts, NBA: 3 pts, MLB: 0.1 runs, NHL: 0.25 goals, Golf: N/A, Soccer: 0.5 goals)

**Weather API (free, no key required):**
```
GET https://api.open-meteo.com/v1/forecast
params: latitude, longitude, hourly=windspeed_10m,precipitation,temperature_2m
```

**Venue coordinates:** Hardcode in config for all major stadiums/venues in scope.

**Acceptance criteria:**
- Returns enriched dict of situational factors for any in-scope sport
- Weather lookup works for NFL/MLB venues
- Returns safe defaults (None) when data unavailable — never crashes

---

### TASK-007: Build ValueDetector
**File to create:** `src/analyzer/value_detector.py`

**What to build:**
Pre-filter that runs BEFORE calling Haiku to avoid wasting API calls.

`ValueDetector.pre_filter(opportunity)` → returns `True` if opportunity is worth analyzing.

Pre-filter criteria (ALL must be met):
1. Best available odds exist for both sides
2. `sum(implied_probs) > 1.0` (not already arbed out — arbs handled separately)
3. At least one side has implied probability between 25% and 75% (avoid extreme favorites)
4. Game is within next 24 hours (for same-day markets) OR is a PGA tournament (multi-day is fine)
5. No existing position in this same game in today's bets log

Also build: `estimate_preliminary_edge(opportunity, situational_factors)` which does a quick heuristic estimate of edge BEFORE Haiku (to prioritize which games go to Haiku first). Sort opportunities by preliminary edge descending.

**Acceptance criteria:**
- Unit tests for each filter condition
- Returns correct boolean for a set of test fixtures
- Correctly sorts a list of 5 mock opportunities by estimated edge

---

### TASK-008: Build ClaudeAnalyzer
**File to create:** `src/analyzer/claude_analyzer.py`

**What to build:**
The core Claude Haiku integration per ARCHITECTURE.md and PRD Section 7.

Key requirements:
- Model: `claude-haiku-4-5-20251001` — NEVER use any other model here
- Max tokens: 1024
- System prompt: exactly as specified in PRD Section 7
- User prompt: built from `build_prompt(opportunity, situational_factors)` using template in PRD Section 7
- Response: MUST be valid JSON matching the schema in PRD Section 7
- `parse_response(raw_text)` validates JSON, raises `AnalysisError` if invalid
- Retry logic: 3 attempts on API error, 2 attempts on JSON parse failure (Haiku occasionally outputs non-JSON — retry)
- Log full raw Haiku response to run log every time (for team training / auditability)

**Golf-specific additions to prompt:**
When sport == "golf_pga", add to the prompt context:
- Tournament name and course
- Player's strokes gained stats (if available from config/static data)
- Recent form: last 5 cuts made / top-10 finishes
- Course fit notes (if in config)
- Market type (outright winner vs. make cut vs. head-to-head)

**Acceptance criteria:**
- Successfully calls Haiku with a sample prompt and receives valid JSON
- `parse_response` correctly handles valid JSON response
- `parse_response` raises `AnalysisError` on invalid JSON (don't crash the run)
- Full prompt logged on every call

---

## PHASE 3 — RISK MANAGER

### TASK-009: Build Risk Manager components
**Files to create:**
- `src/risk_manager/kelly.py`
- `src/risk_manager/kill_switch.py`
- `src/risk_manager/position_limits.py`

**kelly.py — KellyCalculator:**
- `calculate_stake(bankroll, estimated_edge, kelly_fraction, max_bet_pct)` per ARCHITECTURE.md
- Must return 0 if estimated_edge <= 0
- Must never return more than `bankroll × max_bet_pct`
- Round to nearest $0.50 for clean bet sizes

**kill_switch.py — KillSwitch:**
- `is_active()` reads `data/logs/bets_log.csv` for today's entries
- Calculates daily P&L and drawdown %
- Returns True if drawdown >= 40% OR bets_placed >= MAX_DAILY_BETS
- `activate(reason)` logs to `data/logs/kill_switch.log`, sends Telegram alert
- `get_daily_stats()` returns `DailyStats` dataclass

**position_limits.py — PositionLimits:**
- `check(opportunity, existing_bets_today)` → returns `(approved: bool, reason: str)`
- Blocks: same team moneyline AND spread same day (correlated)
- Blocks: more than 1 bet on same game
- Blocks: more than 2 bets on same sport in one day
- Blocks: golf outright winner bet > 2% of bankroll (long-shot cap)

**Acceptance criteria:**
- Kelly unit tests: edge=0.07, bankroll=$1000, fraction=0.25, max=5% → $17.50
- Kelly unit tests: edge=-0.01 → $0.00
- Kill switch unit test: mock CSV with 40% drawdown → returns True
- Kill switch unit test: 0 bets today → returns False
- Position limits: correlated bet blocked correctly

---

## PHASE 4 — EXECUTOR & LOGGING

### TASK-010: Build KalshiExecutor and BetLogger
**Files to create:**
- `src/executor/kalshi_executor.py`
- `src/executor/bet_logger.py`

**KalshiExecutor:**
- `place_bet(bet_order)` → checks `PAPER_MODE`, routes accordingly
- Paper mode: returns `BetResult(status="paper")`, logs simulated bet
- Live mode: POST to Kalshi order endpoint with proper auth
- Always calls `bet_logger.log()` after placement
- Always calls `telegram_bot.send_bet_alert()` after placement

**BetLogger:**
- `log(bet_result)` → appends row to `data/logs/bets_log.csv`
- Schema exactly as specified in PRD Section 10
- `log_pass(opportunity, analysis)` → logs skipped bets (reason=analysis.reasoning)
- `log_arb(arb_result)` → appends to `data/logs/arb_log.csv`
- `get_todays_bets()` → returns today's rows from bets_log.csv as DataFrame
- CSV must be created with headers on first run if it doesn't exist

**Acceptance criteria:**
- Paper bet logged correctly to CSV with all required fields
- `get_todays_bets()` correctly filters by date
- No crash if CSV doesn't exist yet (first run)

---

## PHASE 5 — ALERTING

### TASK-011: Build TelegramBot alerting
**File to create:** `src/alerting/telegram_bot.py`

**What to build:**
`TelegramBot` class that sends formatted messages to a Telegram chat.

Methods:
- `send_bet_alert(bet_result)` → formatted bet placed message
- `send_arb_alert(arb_result)` → formatted arb detection message
- `send_kill_switch_alert(daily_stats)` → kill switch fired message
- `send_daily_summary(daily_stats)` → end-of-day summary
- `send_error(error_msg)` → for critical failures
- All use `requests.post` to Telegram Bot API

**Message formats:**

Bet placed:
```
🎯 PAPER BET PLACED
Sport: NBA | Lakers vs Celtics
Bet: Celtics -3.5 (-108) @ DraftKings
Stake: $22.50 | Edge: 6.2% | Confidence: 74%
Reasoning: Rest advantage (3 days vs 1), strong ATS as road favorite
Bankroll: $977.50 remaining
```

Arb detected:
```
⚡ ARB DETECTED
Sport: NFL | Chiefs vs Ravens
Arb margin: 2.1%
Value side: Ravens +155 @ PointsBet (mispriced)
Implied prob spread: 96.0% total (4% gap)
Action: Bet Ravens +155 as value — do NOT bet both sides
```

Kill switch:
```
🛑 KILL SWITCH ACTIVATED
Reason: Daily drawdown limit reached (42.3%)
Bets today: 2 | P&L: -$87.50
No further bets will be placed today.
```

**Acceptance criteria:**
- Sends message successfully to test chat ID
- Handles Telegram API errors gracefully (log but don't crash the run)
- All message formats match spec above

---

## PHASE 6 — ORCHESTRATION & ENTRY POINT

### TASK-012: Build main.py orchestrator
**File to create:** `main.py`

**What to build:**
The `run_cycle()` function that ties all modules together per ARCHITECTURE.md system diagram.

Full cycle:
1. Load config, initialize logger
2. Check kill switch — if active, log "Kill switch active, skipping cycle" and exit
3. Initialize all module instances (OddsFetcher, ArbDetector, SituationalAnalyzer, etc.)
4. Fetch all odds → `all_markets`
5. Run arb detection on all markets → send Telegram alerts for any arbs found, log to arb_log
6. Run ValueDetector pre-filter → `filtered_opportunities` (sorted by preliminary edge)
7. For each opportunity in filtered_opportunities:
   a. Run SituationalAnalyzer.enrich(opportunity)
   b. Run ClaudeAnalyzer.analyze(opportunity) → AnalysisResult
   c. Log the analysis result (bet or pass) with full reasoning
   d. If recommendation == "pass": log, continue
   e. If recommendation == "bet":
      - Run KillSwitch.is_active() again (re-check before each bet)
      - Run PositionLimits.check()
      - If approved: calculate Kelly stake, place bet via KalshiExecutor
      - Break if MAX_DAILY_BETS reached
8. Log run summary to run_log.csv
9. Exit cleanly

**Error handling:** Catch all exceptions at the top level. Log error. Send Telegram error alert. Exit with code 1 (so scheduler knows the run failed).

---

### TASK-013: Build entry point and scheduler script
**File to create:** `scripts/run_bot.py`

Simple wrapper:
```python
#!/usr/bin/env python3
"""Entry point for Windows Task Scheduler / cron."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import run_cycle
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('data/logs/bot.log'),
        logging.StreamHandler()
    ]
)

if __name__ == "__main__":
    run_cycle()
```

---

## PHASE 7 — TESTS

### TASK-014: Write unit tests
**Files to create:**
- `tests/test_scanner.py` — OddsFetcher.calculate_implied_prob, ArbDetector
- `tests/test_analyzer.py` — ValueDetector pre-filter, ClaudeAnalyzer.parse_response
- `tests/test_risk_manager.py` — KellyCalculator, KillSwitch, PositionLimits
- `tests/test_executor.py` — BetLogger CSV read/write, paper mode execution

**Minimum coverage:**
- kelly.py: 100% (pure math — no excuses)
- kill_switch.py: 90%
- arb_detector.py: 90%
- value_detector.py: 85%
- bet_logger.py: 80%

Use `pytest` and `pytest-mock` for mocking external API calls.

**Acceptance criteria:**
- `pytest tests/` runs with 0 failures
- All edge cases tested: zero edge, zero bankroll, missing data, API timeout

---

## PHASE 8 — DOCS & FINAL SETUP

### TASK-015: Create setup documentation
**File to create:** `docs/setup_guide.md`

Must include:
1. Prerequisites (Python 3.11+, pip)
2. Clone and install steps
3. `.env` setup (where to get each key: Anthropic, The Odds API, Kalshi sandbox, Telegram)
4. How to get a Telegram bot token + chat ID (step by step)
5. Windows Task Scheduler setup (with screenshots described)
6. Hostinger VPS setup (cron job command exact syntax)
7. How to verify the bot is working (check logs, first Telegram message)
8. How to read the bets_log.csv
9. How to switch from paper to live (`PAPER_MODE=false`)
10. Kill switch reset procedure

### TASK-016: Final integration test
**Not a code task — a human verification step. Document in README:**

Before paper trading begins:
- [ ] `python scripts/run_bot.py` runs without errors
- [ ] Telegram receives a test message
- [ ] `data/logs/bets_log.csv` is created on first run
- [ ] `data/logs/run_log.csv` is created on first run
- [ ] Bot correctly reads Kalshi sandbox markets
- [ ] Bot correctly fetches odds from The Odds API
- [ ] Haiku API call returns valid JSON on first test
- [ ] Kill switch correctly blocks bets when triggered
- [ ] Task Scheduler fires correctly at 10-minute intervals

---

## BUILD ORDER SUMMARY

```
TASK-001 → TASK-002 → TASK-003 → TASK-004 → TASK-005
    (setup)     (models)   (scanner)   (arb)    (kalshi data)
        ↓
TASK-006 → TASK-007 → TASK-008
 (situational)  (value)   (claude haiku)
        ↓
TASK-009
 (risk manager: kelly + kill switch + position limits)
        ↓
TASK-010 → TASK-011
  (executor)   (telegram)
        ↓
TASK-012 → TASK-013
  (main.py)    (entry point)
        ↓
TASK-014 → TASK-015 → TASK-016
  (tests)      (docs)    (integration check)
```

**Total estimated build time:** 4-6 hours for Opus working in Claude Code.
