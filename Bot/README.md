# DaftKings Bot
**Automated sports betting analysis and paper trading system**  
Version 1.0 | April 2026

---

## What This Is
An automated pipeline that scans live sports odds, uses Claude Haiku AI to evaluate betting opportunities, manages risk via Kelly Criterion, and executes paper trades on Kalshi. Designed for 1-week paper testing before live deployment.

**Primary platform:** Kalshi (CFTC-regulated, all 50 states, no bet limits)  
**AI model:** Claude Haiku 4.5 (fast, cheap, quality analysis)  
**Sports:** NFL, NBA, MLB, NHL, PGA Tour Golf, Premier League, MLS  
**Philosophy:** Quality over volume — max 2-3 high-confidence bets per day

---

## Quick Start

### 1. Prerequisites
- Python 3.11+
- API keys for: Anthropic, The Odds API, Kalshi (sandbox), Telegram Bot

### 2. Install
```bash
git clone <repo>
cd Bot
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
```

### 3. Run once (test)
```bash
python scripts/run_bot.py
```

### 4. Schedule (Windows)
Set up Windows Task Scheduler to run `scripts/run_bot.py` every 10 minutes.  
See `docs/setup_guide.md` for full instructions.

---

## Key Files
| File | Purpose |
|------|---------|
| `CLAUDE.md` | Instructions for Claude Code / Opus |
| `PRD.md` | Full product requirements |
| `ARCHITECTURE.md` | Technical design |
| `TASKS.md` | Ordered build tasks for development |
| `config.py` | All constants loaded from `.env` |
| `main.py` | Main bot loop |
| `scripts/run_bot.py` | Entry point for scheduler |
| `data/logs/bets_log.csv` | All bets (paper + live) with full metadata |
| `data/logs/arb_log.csv` | Arbitrage detections |

---

## Safety Features
- `PAPER_MODE=true` by default — never risks real money unless explicitly changed
- Kill switch halts all betting at -40% daily drawdown
- Max 3 bets per day — quality filter enforced in code
- All decisions logged with full AI reasoning
- Telegram alerts for every action taken

---

## Paper Trading → Live Checklist
Before setting `PAPER_MODE=false`:
- [ ] 1-week paper run completed
- [ ] Average CLV is positive across all paper bets
- [ ] No kill switch triggers during paper period
- [ ] Kalshi live account funded
- [ ] Kalshi live API credentials configured (not sandbox)
- [ ] Mike has reviewed the full bets_log.csv

---

## Architecture Overview
```
Scheduler (every 10 min)
    → Scanner (The Odds API + Kalshi)
    → Arb Detector (flag value, not both sides)
    → Analyzer (Claude Haiku evaluates each opportunity)
    → Risk Manager (Kelly sizing + kill switch)
    → Executor (Kalshi paper/live order)
    → Logger (CSV) + Telegram alerts
```

See `ARCHITECTURE.md` for full technical diagram.

---

## Integration Test Checklist (TASK-016)

Before paper trading begins, verify each item:

- [ ] `python scripts/run_bot.py` runs without errors
- [ ] Telegram receives a test message
- [ ] `data/logs/bets_log.csv` is created on first run
- [ ] `data/logs/run_log.csv` is created on first run
- [ ] Bot correctly reads Kalshi sandbox markets
- [ ] Bot correctly fetches odds from The Odds API
- [ ] Haiku API call returns valid JSON on first test
- [ ] Kill switch correctly blocks bets when triggered
- [ ] Task Scheduler fires correctly at 10-minute intervals
- [ ] `pytest tests/` passes with 0 failures
