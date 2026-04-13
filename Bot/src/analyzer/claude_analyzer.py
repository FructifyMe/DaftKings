"""Core Claude Haiku integration for bet evaluation. Calls Anthropic API with structured prompts."""

from __future__ import annotations

import json
import logging
import time

import anthropic

from src.models import AnalysisResult, BettingOpportunity

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a professional sports betting analyst for DaftKings, a legal, data-driven betting operation.\n"
    "Evaluate betting opportunities across all sports: NFL, NBA, MLB, NHL, EPL, MLS.\n"
    "You analyze odds, implied probabilities, situational factors (rest, weather, B2B, home advantage), "
    "and cross-book price discrepancies to find genuine value.\n\n"
    "KEY ANALYSIS FRAMEWORK:\n"
    "- Compare implied probability to your estimated true probability\n"
    "- Factor in home/away, rest advantages, weather for outdoor sports, back-to-back fatigue\n"
    "- Cross-book odds divergence signals mispricing — one book may have it right while others are off\n"
    "- Missing data fields (marked N/A) are normal — work with what you have\n"
    "- This is PAPER TRADING — recommend bets when you see edge >= 3%, even if confidence is moderate\n\n"
    "You will respond ONLY with valid JSON. No preamble, no explanation outside the JSON."
)

USER_PROMPT_TEMPLATE = """Evaluate this betting opportunity:

SPORT: {sport}
LEAGUE: {league}
EVENT: {home_team} vs {away_team}
DATE/TIME: {game_time}
MARKET: {market_type}
BEST AVAILABLE ODDS: {odds_summary}
IMPLIED PROBABILITY: {implied_summary}

TEAM RECORDS:
- {home_team}: {home_record} (Home: {home_home_record}) | L10: {home_last_10} | {home_streak}
- {away_team}: {away_record} (Away: {away_away_record}) | L10: {away_last_10} | {away_streak}

RECENT RESULTS:
- {home_team}: {home_recent_results}
- {away_team}: {away_recent_results}

SITUATIONAL FACTORS:
- Rest days (home): {home_rest_days}
- Rest days (away): {away_rest_days}
- Back-to-back: {is_b2b}
- Weather: {weather}

INJURIES:
- {home_team}: {home_injuries}
- {away_team}: {away_injuries}

{sport_specific_context}
ADDITIONAL CONTEXT:
{additional_context}

Evaluate whether there is a genuine betting edge here.
Use ALL available data: team records, recent form, rest advantages, injuries, weather,
pitching matchups (MLB), and cross-book odds divergence to estimate true probability.
Recommend "bet" when estimated edge >= 3%. Your analysis should be data-driven — cite
specific stats (records, streaks, pitcher ERA, injury impact) in your reasoning.

Respond with ONLY this JSON:
{{
  "recommendation": "bet" or "pass",
  "side": "home" or "away" or "over" or "under" or null,
  "bet_description": "Short human-readable bet, e.g. 'Boston Celtics -17.5' or 'Over 222.5' or 'Tampa Bay Lightning ML' or null if pass",
  "bet_odds": American odds integer for the recommended bet (e.g. -108, +169, +112) or null if pass,
  "bet_book": "Bookmaker offering the best price for this bet, e.g. 'fanduel' or 'draftkings' or null if pass",
  "confidence": 0.0-1.0,
  "estimated_edge": 0.00-1.00,
  "estimated_true_probability": 0.00-1.00,
  "key_factors": ["factor1", "factor2", "factor3"],
  "reasoning": "2-3 sentence explanation of the decision"
}}"""

GOLF_CONTEXT_TEMPLATE = """Tournament: {tournament}
Market type: {market_type}
Player strokes gained stats: {strokes_gained}
Recent form (last 5): {recent_form_detail}
Course fit: {course_fit}"""


class AnalysisError(Exception):
    """Raised when Haiku returns invalid or unparseable output."""
    pass


class ClaudeAnalyzer:
    """Calls Claude Haiku to evaluate betting opportunities."""

    MODEL = "claude-haiku-4-5-20251001"
    MAX_TOKENS = 1024

    # Haiku pricing per million tokens (as of 2025)
    INPUT_COST_PER_M = 0.80   # $0.80 per 1M input tokens
    OUTPUT_COST_PER_M = 4.00  # $4.00 per 1M output tokens

    def __init__(self):
        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
        # Running totals for this session
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0
        self.call_count = 0

    def analyze(
        self, opportunity: BettingOpportunity, situational_factors: dict
    ) -> AnalysisResult:
        """Build prompt, call Haiku, parse JSON response.

        Retries: 3 attempts on API error, 2 attempts on JSON parse failure.
        Raises AnalysisError if all retries exhausted.
        """
        prompt = self.build_prompt(opportunity, situational_factors)
        logger.info(
            "Calling Haiku for %s | %s @ %s | %s",
            opportunity.sport, opportunity.away_team,
            opportunity.home_team, opportunity.market_type,
        )
        logger.debug("Full prompt:\n%s", prompt)

        raw_response = self._call_haiku(prompt)
        logger.info("Haiku raw response: %s", raw_response)

        return self.parse_response(raw_response)

    def build_prompt(
        self, opportunity: BettingOpportunity, situational_factors: dict
    ) -> str:
        """Construct the full structured prompt per PRD Section 7."""
        # Build odds summary
        odds_parts = []
        for side, odds in opportunity.best_odds.items():
            odds_parts.append(f"{side}: {odds:+d}")
        odds_summary = " | ".join(odds_parts)

        # Build implied prob summary
        implied_parts = []
        for side, prob in opportunity.implied_probs.items():
            implied_parts.append(f"{side}: {prob:.1%}")
        implied_summary = " | ".join(implied_parts)

        # Additional context for golf
        additional_context = "Standard market."
        if opportunity.sport == "golf_pga":
            additional_context = GOLF_CONTEXT_TEMPLATE.format(
                tournament=opportunity.home_team,
                market_type=opportunity.market_type,
                strokes_gained="N/A (static data not yet loaded)",
                recent_form_detail="N/A",
                course_fit="N/A",
            )

        # Arb context if flagged
        if opportunity.arb_flag and opportunity.arb_result:
            arb = opportunity.arb_result
            additional_context += (
                f"\nARBITRAGE DETECTED: {arb.arb_profit_pct:.1f}% margin. "
                f"Value side: {arb.mispriced_side} at {arb.better_book} ({arb.better_odds:+d}). "
                f"This is a strong mispricing signal."
            )

        weather = situational_factors.get("weather")
        weather_str = "N/A (indoor)" if weather is None else str(weather)

        # Build sport-specific context block
        sport_specific = ""
        home_starter = situational_factors.get("home_starter")
        away_starter = situational_factors.get("away_starter")
        if home_starter or away_starter:
            sport_specific = "PITCHING MATCHUP:\n"
            if home_starter:
                sport_specific += f"- {opportunity.home_team}: {home_starter}\n"
            if away_starter:
                sport_specific += f"- {opportunity.away_team}: {away_starter}\n"
            sport_specific += "\n"

        home_pos = situational_factors.get("home_league_position")
        away_pos = situational_factors.get("away_league_position")
        if home_pos or away_pos:
            sport_specific += "LEAGUE POSITION:\n"
            if home_pos:
                sport_specific += f"- {opportunity.home_team}: #{home_pos}\n"
            if away_pos:
                sport_specific += f"- {opportunity.away_team}: #{away_pos}\n"
            sport_specific += "\n"

        def _val(key: str) -> str:
            v = situational_factors.get(key)
            return str(v) if v is not None else "N/A"

        return USER_PROMPT_TEMPLATE.format(
            sport=opportunity.sport,
            league=opportunity.league,
            home_team=opportunity.home_team,
            away_team=opportunity.away_team,
            game_time=opportunity.game_time.strftime("%Y-%m-%d %H:%M UTC"),
            market_type=opportunity.market_type,
            odds_summary=odds_summary,
            implied_summary=implied_summary,
            home_record=_val("home_record"),
            away_record=_val("away_record"),
            home_home_record=_val("home_home_record"),
            away_away_record=_val("away_away_record"),
            home_last_10=_val("home_last_10"),
            away_last_10=_val("away_last_10"),
            home_streak=_val("home_streak"),
            away_streak=_val("away_streak"),
            home_recent_results=_val("home_recent_results"),
            away_recent_results=_val("away_recent_results"),
            home_rest_days=_val("home_rest_days"),
            away_rest_days=_val("away_rest_days"),
            is_b2b=situational_factors.get("is_b2b", False),
            weather=weather_str,
            home_injuries=_val("home_injuries"),
            away_injuries=_val("away_injuries"),
            sport_specific_context=sport_specific,
            additional_context=additional_context,
        )

    def parse_response(self, raw_text: str) -> AnalysisResult:
        """Parse Haiku's JSON response. Validates all required fields.

        Raises AnalysisError if JSON is invalid or missing required fields.
        """
        # Strip any markdown code fences Haiku might add
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last lines (code fences)
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise AnalysisError(f"Invalid JSON from Haiku: {e}\nRaw: {raw_text[:500]}")

        required_fields = ["recommendation", "confidence", "estimated_edge", "reasoning"]
        for field in required_fields:
            if field not in data:
                raise AnalysisError(f"Missing required field '{field}' in Haiku response")

        recommendation = data["recommendation"]
        if recommendation not in ("bet", "pass"):
            raise AnalysisError(f"Invalid recommendation: {recommendation}")

        # Parse bet_odds safely — Haiku might return string or int
        raw_odds = data.get("bet_odds")
        bet_odds = None
        if raw_odds is not None:
            try:
                bet_odds = int(float(raw_odds))
            except (ValueError, TypeError):
                pass

        return AnalysisResult(
            recommendation=recommendation,
            side=data.get("side"),
            confidence=float(data.get("confidence", 0)),
            estimated_edge=float(data.get("estimated_edge", 0)),
            estimated_true_probability=float(data.get("estimated_true_probability", 0)),
            key_factors=data.get("key_factors", []),
            reasoning=data.get("reasoning", ""),
            raw_haiku_response=raw_text,
            bet_description=data.get("bet_description"),
            bet_odds=bet_odds,
            bet_book=data.get("bet_book"),
        )

    def _call_haiku(self, prompt: str) -> str:
        """Call Haiku with retry logic. 3 attempts on API error, 2 on parse failure."""
        last_error = None

        for attempt in range(3):
            try:
                response = self.client.messages.create(
                    model=self.MODEL,
                    max_tokens=self.MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = response.content[0].text

                # Track token usage and costs
                usage = response.usage
                input_tokens = usage.input_tokens
                output_tokens = usage.output_tokens
                cost = (input_tokens * self.INPUT_COST_PER_M / 1_000_000
                        + output_tokens * self.OUTPUT_COST_PER_M / 1_000_000)
                self.total_input_tokens += input_tokens
                self.total_output_tokens += output_tokens
                self.total_cost_usd += cost
                self.call_count += 1
                logger.info(
                    "Haiku tokens: %d in / %d out = $%.4f (session total: $%.4f / %d calls)",
                    input_tokens, output_tokens, cost, self.total_cost_usd, self.call_count,
                )

                # Validate it's parseable JSON (retry on parse failure up to 2 times)
                try:
                    self.parse_response(raw)
                    return raw
                except AnalysisError as parse_err:
                    if attempt < 2:
                        logger.warning(
                            "Haiku returned invalid JSON (attempt %d), retrying: %s",
                            attempt + 1, parse_err,
                        )
                        time.sleep(1)
                        continue
                    else:
                        raise

            except anthropic.APIError as e:
                last_error = e
                if attempt < 2:
                    wait = 2 ** attempt
                    logger.warning(
                        "Haiku API error (attempt %d), retrying in %ds: %s",
                        attempt + 1, wait, e,
                    )
                    time.sleep(wait)
                else:
                    raise AnalysisError(f"Haiku API failed after 3 attempts: {e}")

        raise AnalysisError(f"Haiku call failed: {last_error}")
