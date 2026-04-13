# DaftKings Bot — Technical Architecture
**Version:** 1.0 | April 2026

---

## OVERVIEW

The DaftKings bot is a scheduled Python pipeline. Every 10 minutes, a single entry point (`scripts/run_bot.py`) is called by Windows Task Scheduler (local dev) or cron (Hostinger VPS). It runs the full scan → analyze → risk → execute cycle, logs all decisions, sends Telegram alerts, and exits cleanly.

No persistent server. No daemon. Stateless per-run, with state persisted to CSV files and `.env` config.

---

## SYSTEM DIAGRAM

```
[Windows Task Scheduler / Cron]
         │  (every 10 minutes)
         ▼
  scripts/run_bot.py
         │
         ├──▶ [SCANNER]
         │        │
         │        ├── odds_fetcher.py
         │        │   └── GET The Odds API /v4/sports/{sport}/odds
         │        │       Returns: all bookmaker lines for upcoming games
         │        │
         │        ├── arb_detector.py
         │        │   └── Calculates implied probs, detects arb (<100% total)
         │        │       Flags: mispriced side → value signal
         │        │
         │        └── kalshi_client.py
         │            └── GET Kalshi market list, current prices
         │
         ├──▶ [ANALYZER] (runs on each flagged opportunity)
         │        │
         │        ├── situational.py
         │        │   └── Rest days, B2B, weather lookup, recent form
         │        │
         │        ├── value_detector.py
         │        │   └── Calculates implied prob vs estimated true prob
         │        │       Pre-filters: edge >= 5%, confidence threshold
         │        │
         │        └── claude_analyzer.py
         │            └── Calls Anthropic API (Haiku)
         │                Sends: structured prompt with all context
         │                Returns: JSON {recommendation, side, confidence,
         │                              estimated_edge, key_factors, reasoning}
         │
         ├──▶ [RISK MANAGER] (runs only on "bet" recommendations)
         │        │
         │        ├── kill_switch.py
         │        │   └── Checks daily_drawdown vs KILL_SWITCH_DRAWDOWN (40%)
         │        │       Checks daily_bets_placed vs MAX_DAILY_BETS (3)
         │        │       → If either limit hit: ABORT, log, Telegram alert
         │        │
         │        ├── position_limits.py
         │        │   └── Checks correlated positions (same team same day)
         │        │       Checks per-sport limits
         │        │
         │        └── kelly.py
         │            └── Calculates stake:
         │                stake = bankroll × edge × KELLY_FRACTION (0.25)
         │                Caps at: bankroll × MAX_BET_PCT (5%)
         │
         ├──▶ [EXECUTOR]
         │        │
         │        ├── kalshi_executor.py
         │        │   └── if PAPER_MODE=true:
         │        │           Simulates bet, returns paper confirmation
         │        │       if PAPER_MODE=false:
         │        │           POST Kalshi demo-api or trading-api order
         │        │
         │        └── bet_logger.py
         │            └── Appends row to data/logs/bets_log.csv
         │                Appends row to data/logs/run_log.csv
         │
         └──▶ [ALERTING]
                  │
                  └── telegram_bot.py
                      └── Sends Telegram message to TELEGRAM_CHAT_ID:
                          - BET PLACED (paper or live)
                          - ARB DETECTED
                          - KILL SWITCH ACTIVATED
                          - Daily summary (11 PM ET run)
```

---

## MODULE SPECIFICATIONS

### `main.py` — Orchestrator
```python
def run_cycle():
    """Main bot cycle. Called by scripts/run_bot.py."""
    # 1. Load config
    # 2. Check kill switch (abort early if already triggered today)
    # 3. Run scanner → get all available markets + odds
    # 4. Run arb detector → flag any cross-book arbs
    # 5. For each opportunity (sorted by estimated edge desc):
    #    a. Run situational filters
    #    b. Pre-filter by edge threshold
    #    c. Call claude_analyzer
    #    d. If recommendation == "bet": run risk manager
    #    e. If risk manager approves: execute bet
    #    f. Log all decisions (bet + pass + arb)
    #    g. Break loop if MAX_DAILY_BETS reached
    # 6. Log run summary
    # 7. Send alerts
    # 8. Exit
```

### `src/scanner/odds_fetcher.py`
```python
class OddsFetcher:
    BASE_URL = "https://api.the-odds-api.com/v4"
    
    def get_odds(self, sport: str, markets: list[str]) -> list[MarketOdds]:
        """Fetch live odds for a sport. Returns normalized MarketOdds objects."""
    
    def get_all_sports(self) -> list[MarketOdds]:
        """Iterate all in-scope sports, return combined opportunity list."""
    
    def calculate_implied_prob(self, american_odds: int) -> float:
        """Convert American odds to implied probability."""
        if american_odds < 0:
            return abs(american_odds) / (abs(american_odds) + 100)
        return 100 / (american_odds + 100)
```

### `src/scanner/arb_detector.py`
```python
class ArbDetector:
    ARB_THRESHOLD = 0.98  # Flag if implied probs sum to < 98%
    
    def detect(self, market: MarketOdds) -> ArbResult | None:
        """
        Returns ArbResult if arbitrage exists.
        ArbResult contains: mispriced_side, better_book, worse_book, 
                           implied_total, value_recommendation
        """
    
    def identify_mispriced_side(self, market: MarketOdds) -> str:
        """
        Returns which side (and which book) has the better price.
        This is the VALUE BET side — not both sides.
        """
```

### `src/analyzer/claude_analyzer.py`
```python
class ClaudeAnalyzer:
    MODEL = "claude-haiku-4-5-20251001"
    MAX_TOKENS = 1024
    
    def __init__(self):
        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    
    def analyze(self, opportunity: BettingOpportunity) -> AnalysisResult:
        """
        Builds structured prompt from opportunity data.
        Calls Haiku. Parses JSON response.
        Returns AnalysisResult with recommendation, confidence, edge, reasoning.
        Raises AnalysisError on API failure (with retry logic).
        """
    
    def build_prompt(self, opportunity: BettingOpportunity) -> str:
        """Constructs the full structured prompt per PRD Section 7."""
    
    def parse_response(self, raw: str) -> AnalysisResult:
        """
        Parses Haiku's JSON response.
        Validates all required fields present.
        Raises ParseError if invalid JSON returned.
        """
```

### `src/risk_manager/kelly.py`
```python
class KellyCalculator:
    def calculate_stake(
        self, 
        bankroll: float, 
        estimated_edge: float,
        kelly_fraction: float = 0.25,
        max_bet_pct: float = 0.05
    ) -> float:
        """
        Calculates Quarter-Kelly stake.
        Formula: stake = bankroll × edge × kelly_fraction
        Hard cap: min(calculated_stake, bankroll × max_bet_pct)
        
        Example:
            bankroll = $1000, edge = 0.07, kelly_fraction = 0.25
            stake = 1000 × 0.07 × 0.25 = $17.50
            cap = 1000 × 0.05 = $50.00
            result = $17.50
        """
```

### `src/risk_manager/kill_switch.py`
```python
class KillSwitch:
    def is_active(self) -> bool:
        """
        Reads today's bets from bets_log.csv.
        Returns True if:
          - daily_drawdown >= KILL_SWITCH_DRAWDOWN (40%), OR
          - bets_placed_today >= MAX_DAILY_BETS (3)
        """
    
    def get_daily_stats(self) -> DailyStats:
        """Returns today's: bets_placed, pnl, drawdown_pct, bankroll_remaining."""
    
    def activate(self, reason: str) -> None:
        """Logs kill switch activation. Sends Telegram alert. Sets flag."""
```

### `src/executor/kalshi_executor.py`
```python
class KalshiExecutor:
    SANDBOX_URL = "https://demo-api.kalshi.co/trade-api/v2"
    LIVE_URL = "https://trading-api.kalshi.com/trade-api/v2"
    
    def place_bet(self, bet: BetOrder) -> BetResult:
        """
        If PAPER_MODE=true: returns simulated BetResult (no API call)
        If PAPER_MODE=false: places real order via Kalshi REST API
        Always: logs to bets_log.csv, triggers Telegram alert
        """
    
    def get_market_price(self, market_id: str) -> float:
        """Fetches current Kalshi market price for a given contract."""
```

---

## DATA MODELS (dataclasses)

```python
@dataclass
class MarketOdds:
    event_id: str
    sport: str
    league: str
    home_team: str
    away_team: str
    game_time: datetime
    market_type: str  # "h2h", "spreads", "totals"
    bookmaker_odds: dict[str, dict]  # {bookmaker: {side: american_odds}}
    best_odds: dict[str, int]  # {side: best_american_odds}
    implied_probs: dict[str, float]  # {side: 0.0-1.0}

@dataclass
class BettingOpportunity(MarketOdds):
    situational_factors: dict
    arb_flag: bool
    arb_result: ArbResult | None

@dataclass
class AnalysisResult:
    recommendation: str  # "bet" or "pass"
    side: str | None
    confidence: float
    estimated_edge: float
    estimated_true_probability: float
    key_factors: list[str]
    reasoning: str
    raw_haiku_response: str

@dataclass
class BetOrder:
    opportunity: BettingOpportunity
    analysis: AnalysisResult
    stake_usd: float
    paper_mode: bool

@dataclass
class BetResult:
    bet_order: BetOrder
    status: str  # "paper", "placed", "failed"
    kalshi_order_id: str | None
    timestamp: datetime
```

---

## CONFIG HIERARCHY

All constants live in `config.py`, populated from `.env`:

```python
# config.py
from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class BotConfig:
    # API Keys
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY")
    odds_api_key: str = os.getenv("ODDS_API_KEY")
    kalshi_api_key: str = os.getenv("KALSHI_API_KEY")
    
    # Behavior
    paper_mode: bool = os.getenv("PAPER_MODE", "true").lower() == "true"
    starting_bankroll: float = float(os.getenv("STARTING_BANKROLL", "1000"))
    kelly_fraction: float = float(os.getenv("KELLY_FRACTION", "0.25"))
    max_daily_bets: int = int(os.getenv("MAX_DAILY_BETS", "3"))
    min_edge_threshold: float = float(os.getenv("MIN_EDGE_THRESHOLD", "0.05"))
    kill_switch_drawdown: float = float(os.getenv("KILL_SWITCH_DRAWDOWN", "0.40"))
    max_bet_pct: float = float(os.getenv("MAX_BET_PCT", "0.05"))
    
    # Alerting
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID")
    
    # Sports
    active_sports: list[str] = None
    
    def __post_init__(self):
        if self.active_sports is None:
            self.active_sports = [
                "americanfootball_nfl",
                "basketball_nba",
                "baseball_mlb", 
                "icehockey_nhl",
                "golf_pga",
                "soccer_epl",
                "soccer_usa_mls"
            ]

CONFIG = BotConfig()
```

---

## SCHEDULING SETUP

### Windows Task Scheduler (Local Dev)
```
Action: Start a program
Program: C:\Python311\python.exe
Arguments: C:\path\to\DaftKings\Bot\scripts\run_bot.py
Trigger: Every 10 minutes, daily
Run whether user is logged on or not
```

### Cron (Hostinger VPS / Ubuntu)
```cron
*/10 * * * * /usr/bin/python3 /home/daftkings/Bot/scripts/run_bot.py >> /home/daftkings/Bot/data/logs/cron.log 2>&1
# Daily summary at 11 PM ET (UTC+4 in summer)
0 3 * * * /usr/bin/python3 /home/daftkings/Bot/scripts/daily_summary.py >> /home/daftkings/Bot/data/logs/cron.log 2>&1
```

---

## ERROR HANDLING STRATEGY

Every external API call follows this pattern:
```python
import time
import logging

def api_call_with_retry(func, *args, retries=3, backoff=2, **kwargs):
    """Retry wrapper with exponential backoff."""
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == retries - 1:
                logging.error(f"API call failed after {retries} attempts: {e}")
                raise
            wait = backoff ** attempt
            logging.warning(f"Attempt {attempt+1} failed, retrying in {wait}s: {e}")
            time.sleep(wait)
```

Errors are never fatal to the full run. If the scanner fails for one sport, the bot continues with other sports. If Haiku is unavailable, log the error and skip that opportunity — do not guess.

---

## COST ESTIMATE (Haiku API)

| Scenario | Calls/day | Tokens/call | Daily cost |
|----------|-----------|-------------|------------|
| Active market day (10+ games) | ~30 | ~800 in + 200 out | ~$0.04 |
| Heavy day (NFL Sunday) | ~80 | ~800 in + 200 out | ~$0.10 |
| Monthly estimate | — | — | ~$1.50-3.00 |

Haiku pricing (as of 2026): ~$0.00025/1K input tokens, ~$0.00125/1K output tokens.  
Cost is negligible relative to any real betting activity.
