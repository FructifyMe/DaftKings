# DaftKings Bot — Claude Code Instructions for Opus

## WHAT YOU ARE BUILDING
An automated sports betting analysis bot for DaftKings, a legal sports betting company. This bot:
- Runs on a schedule (Windows Task Scheduler locally, then cron on Hostinger VPS)
- Pulls live odds from The Odds API
- Uses Claude Haiku (via Anthropic API) to analyze betting opportunities
- Detects arbitrage opportunities and flags them (does NOT hammer arbs — flags them as value signals)
- Applies quality filters (max 2-3 bets/day, minimum 5% edge)
- Manages risk via Kelly Criterion + kill switch
- Logs to CSV and sends Telegram alerts
- Executes paper trades on Kalshi (primary platform) during testing phase

## OWNER CONTEXT
- Owner: Mike
- Stage: Paper trading (1-week test) → Live on Kalshi
- Bot-friendly platform: Kalshi (CFTC-regulated exchange, all 50 states, no limits for winners)
- Never deploy real money without explicit instruction — paper mode first

## CRITICAL DESIGN PRINCIPLES
1. **Quality over volume**: Surface 2-3 high-confidence bets per day MAX. Do not bet noise.
2. **Kalshi is primary**: Build executor for Kalshi API first. Traditional sportsbook execution is Phase 2.
3. **Haiku for the loop**: All per-cycle analysis calls use `claude-haiku-4-5-20251001`. Never use Sonnet/Opus in the hot path.
4. **Arb = value signal**: When arbitrage is detected, flag the mispriced side as a value bet — do not bet both sides.
5. **Kill switch is sacred**: If daily drawdown exceeds 40%, all betting halts. No exceptions. No overrides.
6. **Log everything**: Every decision (including passes/skips) must be logged with full reasoning for audit.
7. **Paper mode by default**: All execution code must check `PAPER_MODE=true` env var before placing any real order.

## ANTHROPIC API USAGE
```python
import anthropic

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

response = client.messages.create(
    model="claude-haiku-4-5-20251001",  # Haiku ONLY in hot path
    max_tokens=1024,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": analysis_prompt}]
)

analysis = response.content[0].text
```

## SPORTS IN SCOPE
NFL, NBA, MLB, NHL, PGA Tour (Golf), Premier League, MLS

## FOLDER STRUCTURE (DO NOT CHANGE)
```
Bot/
├── CLAUDE.md          ← you are here
├── PRD.md             ← full requirements
├── ARCHITECTURE.md    ← technical design
├── README.md          ← setup guide
├── TASKS.md           ← build order
├── .env.example       ← env var template
├── requirements.txt
├── config.py          ← all constants, thresholds, sport configs
├── main.py            ← entry point, orchestrates the full loop
├── src/
│   ├── scanner/
│   │   ├── odds_fetcher.py     ← The Odds API integration
│   │   ├── kalshi_client.py    ← Kalshi API (market data + execution)
│   │   └── arb_detector.py     ← Cross-book arb detection
│   ├── analyzer/
│   │   ├── claude_analyzer.py  ← Haiku API calls for bet evaluation
│   │   ├── value_detector.py   ← Edge calculation (model prob vs implied prob)
│   │   └── situational.py      ← Rest, weather, B2B, travel factors
│   ├── risk_manager/
│   │   ├── kelly.py            ← Kelly Criterion (quarter-Kelly default)
│   │   ├── kill_switch.py      ← Daily drawdown monitor
│   │   └── position_limits.py  ← Max per bet, per sport, per day
│   ├── executor/
│   │   ├── kalshi_executor.py  ← Paper + live order placement
│   │   └── bet_logger.py       ← CSV logging with full metadata
│   └── alerting/
│       └── telegram_bot.py     ← Telegram notifications
├── data/
│   ├── historical/             ← Store fetched historical odds
│   └── logs/                   ← bets_log.csv, errors.log
├── tests/
│   ├── test_scanner.py
│   ├── test_analyzer.py
│   ├── test_risk_manager.py
│   └── test_executor.py
├── docs/
│   ├── setup_guide.md
│   └── kalshi_api_guide.md
└── scripts/
    └── run_bot.py              ← Called by Task Scheduler / cron
```

## ENV VARS REQUIRED
```
ANTHROPIC_API_KEY=
ODDS_API_KEY=
KALSHI_API_KEY=
KALSHI_API_SECRET=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
PAPER_MODE=true
STARTING_BANKROLL=1000
KELLY_FRACTION=0.25
MAX_DAILY_BETS=3
MIN_EDGE_THRESHOLD=0.05
KILL_SWITCH_DRAWDOWN=0.40
MAX_BET_PCT=0.05
```

## CODE QUALITY REQUIREMENTS
- Full type hints on all functions
- Docstrings on all public methods
- All API calls wrapped in try/except with logging
- No hardcoded values — everything via config.py or .env
- Unit tests for kelly.py, kill_switch.py, value_detector.py, arb_detector.py
- Write modular code — each module is independently testable
- Never commit API keys — .env is in .gitignore

## DO NOT BUILD (YET — PHASE 2)
- DraftKings / FanDuel API integration
- XGBoost ML model (Phase 2)
- Live betting (in-game) module
- Web dashboard
