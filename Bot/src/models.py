"""DaftKings Bot data models. All core dataclasses used across modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MarketOdds:
    """Raw odds data for a single market from The Odds API."""

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

    def __repr__(self) -> str:
        return (
            f"MarketOdds({self.sport} | {self.away_team} @ {self.home_team} | "
            f"{self.market_type} | {self.game_time:%Y-%m-%d %H:%M})"
        )


@dataclass
class ArbResult:
    """Result of an arbitrage detection scan on a single market."""

    event_id: str
    sport: str
    home_team: str
    away_team: str
    market_type: str
    mispriced_side: str  # "home" or "away" or "over" or "under"
    better_book: str  # bookmaker with the value price
    worse_book: str  # bookmaker on the other side
    better_odds: int  # American odds on the value side
    implied_total: float  # sum of implied probs (< 1.0 means arb)
    arb_profit_pct: float  # (1 - implied_total) * 100
    value_recommendation: str  # human-readable recommendation

    def __repr__(self) -> str:
        return (
            f"ArbResult({self.away_team} @ {self.home_team} | "
            f"arb {self.arb_profit_pct:.1f}% | value: {self.mispriced_side} "
            f"at {self.better_book})"
        )


@dataclass
class BettingOpportunity:
    """A MarketOdds enriched with situational context and arb flags."""

    # Core market data (same as MarketOdds)
    event_id: str
    sport: str
    league: str
    home_team: str
    away_team: str
    game_time: datetime
    market_type: str
    bookmaker_odds: dict[str, dict]
    best_odds: dict[str, int]
    implied_probs: dict[str, float]

    # Enrichment
    situational_factors: dict = field(default_factory=dict)
    arb_flag: bool = False
    arb_result: ArbResult | None = None
    preliminary_edge: float = 0.0

    @classmethod
    def from_market_odds(cls, market: MarketOdds, **kwargs) -> BettingOpportunity:
        """Create a BettingOpportunity from a MarketOdds instance."""
        return cls(
            event_id=market.event_id,
            sport=market.sport,
            league=market.league,
            home_team=market.home_team,
            away_team=market.away_team,
            game_time=market.game_time,
            market_type=market.market_type,
            bookmaker_odds=market.bookmaker_odds,
            best_odds=market.best_odds,
            implied_probs=market.implied_probs,
            **kwargs,
        )

    def __repr__(self) -> str:
        arb = " [ARB]" if self.arb_flag else ""
        return (
            f"BettingOpportunity({self.sport} | {self.away_team} @ {self.home_team} | "
            f"{self.market_type}{arb})"
        )


@dataclass
class AnalysisResult:
    """Structured output from Claude Haiku's bet evaluation."""

    recommendation: str  # "bet" or "pass"
    side: str | None  # "home", "away", "over", "under", or None
    confidence: float  # 0.0-1.0
    estimated_edge: float  # 0.0-1.0
    estimated_true_probability: float  # 0.0-1.0
    key_factors: list[str]
    reasoning: str
    raw_haiku_response: str
    bet_description: str | None = None  # e.g. "Boston Celtics -17.5", "Over 222.5"
    bet_odds: int | None = None  # American odds, e.g. -108, +169
    bet_book: str | None = None  # Best bookmaker, e.g. "fanduel"

    def __repr__(self) -> str:
        return (
            f"AnalysisResult({self.recommendation} | side={self.side} | "
            f"conf={self.confidence:.0%} | edge={self.estimated_edge:.1%})"
        )


@dataclass
class BetOrder:
    """A fully approved bet ready for execution."""

    opportunity: BettingOpportunity
    analysis: AnalysisResult
    stake_usd: float
    paper_mode: bool

    def __repr__(self) -> str:
        mode = "PAPER" if self.paper_mode else "LIVE"
        return (
            f"BetOrder({mode} | {self.opportunity.sport} | "
            f"{self.analysis.side} | ${self.stake_usd:.2f})"
        )


@dataclass
class BetResult:
    """Outcome of a bet placement attempt."""

    bet_order: BetOrder
    status: str  # "paper", "placed", "failed"
    kalshi_order_id: str | None
    timestamp: datetime

    def __repr__(self) -> str:
        return (
            f"BetResult({self.status} | {self.bet_order.opportunity.sport} | "
            f"${self.bet_order.stake_usd:.2f} | {self.timestamp:%H:%M:%S})"
        )


@dataclass
class DailyStats:
    """Aggregated stats for the current trading day."""

    date: str
    bets_placed: int
    total_staked: float
    pnl_usd: float
    drawdown_pct: float
    bankroll_remaining: float
    kill_switch_active: bool

    def __repr__(self) -> str:
        status = "KILLED" if self.kill_switch_active else "ACTIVE"
        return (
            f"DailyStats({self.date} | {self.bets_placed} bets | "
            f"P&L ${self.pnl_usd:+.2f} | DD {self.drawdown_pct:.1%} | {status})"
        )
