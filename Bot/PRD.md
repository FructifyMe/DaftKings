# DaftKings Bot — Product Requirements Document (PRD)
**Version:** 1.0  
**Date:** April 2026  
**Owner:** Mike (DaftKings)  
**Status:** Ready for development

---

## 1. PROBLEM STATEMENT

Sports betting markets contain mispriced lines that represent exploitable edges. Identifying these edges manually — across multiple sports, multiple books, and multiple markets simultaneously — is impossible at the speed required. A systematic, automated approach to scanning, analyzing, and logging quality bet opportunities is required to build a professional, data-driven betting operation.

The bot must train the team on how edge detection works, generate an auditable paper-trading track record, and be ready to flip to live execution on Kalshi with minimal code changes.

---

## 2. GOALS

### Primary Goals
- Automatically scan live odds across NFL, NBA, MLB, NHL, PGA Tour (Golf), Premier League, and MLS
- Use Claude Haiku to analyze each opportunity and evaluate whether it meets quality criteria
- Surface a maximum of **2-3 high-confidence bets per day** (quality over volume)
- Log all decisions (both bets placed AND bets skipped) with full AI reasoning
- Alert the team via Telegram for every placed bet and every arb flag
- Operate in paper mode for a minimum of 1 week before live deployment

### Secondary Goals
- Detect cross-book arbitrage and flag the mispriced side as a value signal
- Track Closing Line Value (CLV) on every bet to evaluate model quality
- Build a foundation that can be extended with XGBoost ML models in Phase 2

### Out of Scope (Phase 1)
- Live/in-game betting
- DraftKings / FanDuel API execution
- XGBoost model training
- Web dashboard or UI
- Parlay / teaser construction

---

## 3. USER STORIES

**As the DaftKings operator, I want to:**
- See a Telegram message every time the bot identifies and places a paper bet, so I can follow along in real time
- See a Telegram alert when an arbitrage opportunity is detected, including which book has the mispriced line, so I can manually act on it if I choose
- Review a complete CSV log of every bet the bot considered and why it did or didn't place it
- Know the bot will never bet real money unless I change `PAPER_MODE=false` in the config
- Know the bot will automatically stop betting if it loses 40% of the day's allocated bankroll

**As a DaftKings staff member (trainee), I want to:**
- Read the bot's reasoning (Claude Haiku output) for every bet so I can learn what factors drive quality decisions
- See which sports and bet types are generating the most edge signals
- Understand why the bot passed on a game as much as why it bet it

---

## 4. SPORTS & MARKETS IN SCOPE

| Sport | League | Bet Types | Key Factors |
|-------|--------|-----------|-------------|
| American Football | NFL | Spread, Moneyline, Totals | Key numbers (3,7), weather, rest |
| Basketball | NBA | Spread, Moneyline, Totals | Back-to-back, rest diff, pace |
| Baseball | MLB | Moneyline, Run Line, Totals, F5 | Pitcher matchup, park factor, weather |
| Ice Hockey | NHL | Moneyline, Puck Line, Totals | Goalie confirmed, B2B, rest |
| Golf | PGA Tour | Outright winner, Top 5/10/20, Make Cut, Head-to-head | Course history, strokes gained, current form, putting stats |
| Soccer | Premier League | 1X2, Asian Handicap, O/U Goals | Squad rotation, home/away form |
| Soccer | MLS | 1X2, Asian Handicap, O/U Goals | Travel distance, home advantage |

### Golf-Specific Notes
Golf is the most inefficient major market available — books price tournaments days in advance with limited information, and closing lines move significantly as sharp money comes in. Key edges:
- **Strokes Gained** analytics (Approach, Putting, Off-the-Tee, Around-the-Green)
- **Course fit**: Does the player's game fit the course? (Long hitter at Augusta vs. iron player)
- **Recent form**: Last 5 starts, cuts made, top-10 finishes
- **Head-to-head matchups**: Two-ball and three-ball markets are among the most beatable in sports
- **Make/Miss Cut props**: Highly inefficient, especially for mid-tier players

---

## 5. FUNCTIONAL REQUIREMENTS

### 5.1 Scanner Module
- **FR-01**: Fetch live and upcoming odds from The Odds API every 5-10 minutes
- **FR-02**: Support all sports listed in Section 4
- **FR-03**: Pull odds from at minimum 5 bookmakers for each event
- **FR-04**: Detect arbitrage opportunities (when implied probabilities across two books sum to less than 100%)
- **FR-05**: Track opening line vs. current line to detect steam moves
- **FR-06**: Store raw odds data to `data/historical/` in CSV format for future ML training

### 5.2 Analyzer Module
- **FR-07**: For each market, calculate implied probability from best available odds
- **FR-08**: Apply situational filters (rest differential, back-to-back, weather if applicable)
- **FR-09**: Call Claude Haiku API with a structured prompt containing: sport, teams, current odds, situational factors, recent form signals, and sharp/public data if available
- **FR-10**: Claude Haiku returns a structured JSON response: `{recommendation: "bet"|"pass", side: str, confidence: float, estimated_edge: float, reasoning: str}`
- **FR-11**: Only forward to Risk Manager if `confidence >= 0.70` AND `estimated_edge >= 0.05` (5%)
- **FR-12**: Log all analyzer outputs (bet AND pass decisions) to CSV

### 5.3 Arbitrage Detector
- **FR-13**: When two books price the same market such that implied probabilities sum to < 98%, flag as arb
- **FR-14**: Identify which side is mispriced (i.e., which book has the "wrong" price)
- **FR-15**: Flag the mispriced side as a potential VALUE bet (do not bet both sides)
- **FR-16**: Send Telegram alert: `ARB DETECTED: [Game] | [Team A] at [Book1] +[odds] vs [Book2]. Mispriced side: [Team] — recommend value bet.`
- **FR-17**: Log all arb detections to `data/logs/arb_log.csv`

### 5.4 Risk Manager
- **FR-18**: Apply Quarter-Kelly formula to size every bet: `stake = bankroll × (edge × kelly_fraction)`
- **FR-19**: Cap any single bet at 5% of total bankroll (hard limit, not overridable)
- **FR-20**: Track daily P&L from `data/logs/bets_log.csv`
- **FR-21**: If daily drawdown exceeds 40% of day's starting bankroll, activate kill switch — log "KILL SWITCH ACTIVATED", send Telegram alert, refuse all further bets until next day
- **FR-22**: Cap total bets per day at `MAX_DAILY_BETS` (default: 3)
- **FR-23**: Prevent correlated bets (e.g., same team's moneyline AND spread on same day)

### 5.5 Executor
- **FR-24**: Check `PAPER_MODE` env var — if `true`, simulate placement only (log as paper bet, do not call Kalshi order API)
- **FR-25**: If `PAPER_MODE=false`, place order via Kalshi REST API
- **FR-26**: Record bet in `data/logs/bets_log.csv` with: timestamp, sport, league, event, market, bet_side, price_obtained, stake, paper_mode, kalshi_order_id (if live)
- **FR-27**: On game completion (or next scan cycle), attempt to fetch result and log outcome: W/L/Push, P&L, closing line, CLV

### 5.6 Alerting
- **FR-28**: Send Telegram message for every placed bet (paper or live)
- **FR-29**: Send Telegram message for every arb detection
- **FR-30**: Send Telegram message when kill switch activates
- **FR-31**: Send daily summary at 11 PM ET: bets placed, P&L, CLV average, bankroll balance

### 5.7 Scheduling
- **FR-32**: `scripts/run_bot.py` serves as the single entry point called by scheduler
- **FR-33**: Designed to run every 10 minutes via Windows Task Scheduler (dev) or cron (VPS)
- **FR-34**: Bot must complete full cycle and exit cleanly — no persistent processes required
- **FR-35**: Log all runs (start time, end time, bets evaluated, bets placed) to `data/logs/run_log.csv`

---

## 6. NON-FUNCTIONAL REQUIREMENTS

- **NFR-01 Performance**: Full scan-analyze-decide cycle must complete within 60 seconds
- **NFR-02 Reliability**: All API calls have retry logic (3 retries with exponential backoff)
- **NFR-03 Security**: No API keys in source code; all via `.env` file (gitignored)
- **NFR-04 Testability**: Core modules (kelly.py, kill_switch.py, value_detector.py, arb_detector.py) have unit tests with 80%+ coverage
- **NFR-05 Auditability**: Every decision logged — including skipped bets — with Claude's full reasoning text
- **NFR-06 Cost efficiency**: Only Claude Haiku used in the hot path. Max 2,000 tokens per Haiku call.
- **NFR-07 Portability**: Runs on Windows (local dev) and Ubuntu 22.04 (Hostinger VPS) without code changes

---

## 7. CLAUDE HAIKU PROMPT SPECIFICATION

The analyzer module calls Haiku with the following structured prompt. Haiku must return valid JSON only.

### System Prompt
```
You are a professional sports betting analyst for DaftKings, a legal, data-driven betting operation.
Your job is to evaluate betting opportunities and determine if they represent genuine value.
You must be selective — only recommend bets when there is clear edge.
You will respond ONLY with valid JSON. No preamble, no explanation outside the JSON.
```

### User Prompt Template
```
Evaluate this betting opportunity:

SPORT: {sport}
LEAGUE: {league}
EVENT: {home_team} vs {away_team}
DATE/TIME: {game_time}
MARKET: {market_type}
BEST AVAILABLE ODDS: {side_a}: {odds_a} | {side_b}: {odds_b}
IMPLIED PROBABILITY: {side_a}: {implied_prob_a:.1%} | {side_b}: {implied_prob_b:.1%}

SITUATIONAL FACTORS:
- Rest days (home): {home_rest_days}
- Rest days (away): {away_rest_days}
- Back-to-back: {is_b2b}
- Weather (if applicable): {weather}
- Recent form: {recent_form}
- Sharp money signal: {sharp_signal}
- Public betting %: {public_pct}

ADDITIONAL CONTEXT:
{additional_context}

Evaluate whether there is a genuine betting edge here.
Consider: implied probability vs true probability, situational advantages, sharp money signals.
Only recommend if estimated edge is at least 5%.

Respond with ONLY this JSON:
{
  "recommendation": "bet" or "pass",
  "side": "home" or "away" or "over" or "under" or null,
  "confidence": 0.0-1.0,
  "estimated_edge": 0.00-1.00,
  "estimated_true_probability": 0.00-1.00,
  "key_factors": ["factor1", "factor2", "factor3"],
  "reasoning": "2-3 sentence explanation of the decision"
}
```

---

## 8. KALSHI API INTEGRATION SPEC

### Authentication
```python
# RSA key pair authentication
import kalshi_python

config = kalshi_python.Configuration(host="https://trading-api.kalshi.com/trade-api/v2")
config.api_key['ApiKeyAuth'] = os.getenv('KALSHI_API_KEY')
# Sign each request with private key PEM
```

### Paper Mode Logic
```python
def place_bet(market_id: str, side: str, stake: float, paper_mode: bool = True):
    if paper_mode:
        logger.info(f"PAPER BET: {market_id} | {side} | ${stake:.2f}")
        return {"status": "paper", "market_id": market_id, "stake": stake}
    else:
        # Real Kalshi API call
        return kalshi_client.create_order(market_id, side, stake)
```

### Sandbox Environment
Use `https://demo-api.kalshi.co/trade-api/v2` for paper trading (Kalshi's official sandbox).

---

## 9. THE ODDS API INTEGRATION SPEC

**Endpoint:** `GET https://api.the-odds-api.com/v4/sports/{sport}/odds`

**Required params:**
- `apiKey`: from env
- `regions`: us (for US books), eu (for international comparison)
- `markets`: h2h (moneyline), spreads, totals
- `oddsFormat`: american
- `bookmakers`: draftkings,fanduel,betmgm,caesars,pointsbet

**Response handling:** Parse the JSON, extract all bookmakers' prices for each market, find best available price per side, calculate implied probability from American odds.

---

## 10. BETTING LOG SCHEMA

`data/logs/bets_log.csv` columns:
```
timestamp, run_id, sport, league, event_id, home_team, away_team, 
game_time, market_type, recommended_side, best_odds, implied_prob,
estimated_true_prob, estimated_edge, confidence, kelly_stake_pct,
actual_stake_usd, paper_mode, kalshi_order_id, result, pnl_usd,
closing_odds, clv_points, haiku_reasoning, arb_flag, arb_books
```

---

## 11. PHASE 2 FEATURES (NOT NOW)
- XGBoost model for each sport (train on historical data from The Odds API + SportsDataIO)
- Feature engineering pipeline (ATS history, rest days, travel, SOS, park factors)
- Backtesting framework with walk-forward analysis
- DraftKings / FanDuel execution layer (with account protection protocols)
- Web monitoring dashboard (React + recharts)
- Live/in-game betting module (WebSocket odds feed)
- Parlay builder (for favorable correlated markets)

---

## 12. SUCCESS METRICS (Paper Trading Phase)

After 1 week of paper trading, evaluate:

| Metric | Target | Action if Missed |
|--------|--------|-----------------|
| Average CLV | > 0 (positive) | Review edge threshold, tighten filters |
| Bets placed per day | 1-3 | If >3, raise confidence threshold |
| Arb detections per day | 1-5 | Expected range, monitor for quality |
| Bot uptime | 100% cycle completion | Debug scheduler, fix API errors |
| Kill switch triggers | 0 | Good — means risk rules working |
| Simulated ROI | Track only, no target | Baseline for live deployment decision |
