"""DaftKings Bot configuration. All constants loaded from .env with sensible defaults."""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv(override=True)


@dataclass
class BotConfig:
    # API Keys
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    odds_api_key: str = os.getenv("ODDS_API_KEY", "")
    kalshi_api_key: str = os.getenv("KALSHI_API_KEY", "")
    kalshi_api_secret: str = os.getenv("KALSHI_API_SECRET", "")

    # Behavior
    paper_mode: bool = os.getenv("PAPER_MODE", "true").lower() == "true"
    starting_bankroll: float = float(os.getenv("STARTING_BANKROLL", "1000"))
    kelly_fraction: float = float(os.getenv("KELLY_FRACTION", "0.25"))
    max_daily_bets: int = int(os.getenv("MAX_DAILY_BETS", "3"))
    min_edge_threshold: float = float(os.getenv("MIN_EDGE_THRESHOLD", "0.05"))
    kill_switch_drawdown: float = float(os.getenv("KILL_SWITCH_DRAWDOWN", "0.40"))
    max_bet_pct: float = float(os.getenv("MAX_BET_PCT", "0.05"))

    # Alerting
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # Sports (The Odds API sport keys)
    active_sports: list[str] = field(default_factory=lambda: [
        "americanfootball_nfl",
        "basketball_nba",
        "baseball_mlb",
        "icehockey_nhl",
        # Golf — major tournament futures (keys come/go with tournaments)
        "golf_masters_tournament_winner",
        "golf_pga_championship_winner",
        "golf_the_open_championship_winner",
        "golf_us_open_winner",
        # Tennis — event-driven (keys appear during active tournaments)
        "tennis_atp_monte_carlo_masters",
        # Soccer
        "soccer_epl",
        "soccer_usa_mls",
    ])

    # The Odds API regions — controls which bookmakers appear in results
    # us=US licensed, us2=offshore/secondary US, eu=European (Pinnacle, Betfair)
    odds_api_regions: str = "us,us2,eu"

    # No bookmaker filter — let ALL books from the selected regions through
    # This gives us 30-50 books including Pinnacle (sharpest) and Betfair (exchange)
    bookmakers: list[str] = field(default_factory=list)  # empty = no filter = all books

    # Kalshi URLs
    kalshi_sandbox_url: str = "https://demo-api.kalshi.co/trade-api/v2"
    kalshi_live_url: str = "https://trading-api.kalshi.com/trade-api/v2"

    @property
    def kalshi_base_url(self) -> str:
        """Returns sandbox URL unless paper mode is explicitly off."""
        if self.paper_mode:
            return self.kalshi_sandbox_url
        return self.kalshi_live_url

    # Retry settings
    api_retries: int = 3
    api_backoff: int = 2

    # Home advantage defaults by sport
    home_advantage: dict[str, float] = field(default_factory=lambda: {
        "americanfootball_nfl": 3.0,
        "basketball_nba": 3.0,
        "baseball_mlb": 0.1,
        "icehockey_nhl": 0.25,
        "golf_masters_tournament_winner": 0.0,
        "golf_pga_championship_winner": 0.0,
        "golf_the_open_championship_winner": 0.0,
        "golf_us_open_winner": 0.0,
        "tennis_atp_monte_carlo_masters": 0.0,
        "soccer_epl": 0.5,
        "soccer_usa_mls": 0.5,
    })


CONFIG = BotConfig()
