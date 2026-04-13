# DaftKings — Sports Betting Knowledge Base
### Staff Training Reference | Version 2.0 | April 2026

> **Purpose:** This is the master reference document for all DaftKings staff. It covers sports betting from first principles to professional-grade strategy, with historical data across all major leagues, a full bot development blueprint, and coverage of emerging prediction market platforms (Kalshi, Polymarket). Study this front to back before operating.

---

## TABLE OF CONTENTS
1. [The Business of Sports Betting](#1-the-business-of-sports-betting)
2. [Understanding Odds](#2-understanding-odds)
3. [Bet Types Explained](#3-bet-types-explained)
4. [The Vig, Juice & Implied Probability](#4-the-vig-juice--implied-probability)
5. [How Sportsbooks Set Lines](#5-how-sportsbooks-set-lines)
6. [Professional Betting Strategies](#6-professional-betting-strategies)
7. [Bankroll Management](#7-bankroll-management)
8. [Sharp vs. Public Money](#8-sharp-vs-public-money)
9. [Closing Line Value (CLV)](#9-closing-line-value-clv)
10. [NFL — Data, Trends & Strategy](#10-nfl--data-trends--strategy)
11. [NBA — Data, Trends & Strategy](#11-nba--data-trends--strategy)
12. [MLB — Data, Trends & Strategy](#12-mlb--data-trends--strategy)
13. [NHL — Data, Trends & Strategy](#13-nhl--data-trends--strategy)
14. [Soccer — Premier League & MLS](#14-soccer--premier-league--mls)
15. [Prediction Markets — Kalshi & Polymarket](#15-prediction-markets--kalshi--polymarket)
16. [Machine Learning & Bot Development](#16-machine-learning--bot-development)
17. [Claude + MCP Bot Stack (Production Blueprint)](#17-claude--mcp-bot-stack-production-blueprint)
18. [Data Sources & APIs](#18-data-sources--apis)
19. [Legal Landscape (US)](#19-legal-landscape-us)
20. [Glossary](#20-glossary)

---

## 1. THE BUSINESS OF SPORTS BETTING

### What This Business Actually Is
Sports betting is a **market**. Like financial markets, price (odds) reflects the aggregated knowledge of all participants. The sportsbook is the market maker. Professional bettors are like quantitative traders — they find edges (mispricings) and exploit them systematically.

The key insight: **you are not trying to predict who wins. You are trying to find when the price is wrong.**

### Market Size
- US legal sports betting handle exceeded **$121 billion in 2023**
- The global AI sports prediction market is projected to grow from $1.3B (2025) to $6.3B (2033)
- AI-traded bets now account for **48% of activity** on major betting networks (up from 28% in prior years)
- Top US markets: New York ($19B handle), New Jersey ($11.9B), Illinois ($11.6B), Pennsylvania ($7.6B)

### How Sportsbooks Make Money
A sportsbook does not need to predict outcomes. It needs **balanced action** on both sides, collecting the vig from every bet. If $110 is bet on each side of a game, the book collects $220, pays out $210 to the winner, and keeps $10 — regardless of who wins.

The sportsbook's enemy is not a losing bettor. It's a **sharp bettor who consistently beats the closing line**.

---

## 2. UNDERSTANDING ODDS

### American Odds (Moneyline Format)
The most common format in the US.

**Negative odds** = favorite. The number tells you how much you must bet to win $100.
- Example: -150 means bet $150 to win $100 (total return: $250)

**Positive odds** = underdog. The number tells you how much you win on a $100 bet.
- Example: +130 means bet $100 to win $130 (total return: $230)

### Converting Odds to Implied Probability
**Negative odds:** `Implied Probability = |Odds| / (|Odds| + 100)`
- Example: -150 → 150 / 250 = **60%**

**Positive odds:** `Implied Probability = 100 / (Odds + 100)`
- Example: +130 → 100 / 230 = **43.5%**

### The Overround (Why They Don't Add to 100%)
If -150/+130 represent a game, the two implied probabilities are 60% + 43.5% = **103.5%**. That extra 3.5% is the **vig** — the book's built-in margin.

### Decimal Odds (Common in Europe/Soccer)
- 1.67 (equivalent to -150 American)
- 2.30 (equivalent to +130 American)
- **Formula:** `Implied Probability = 1 / Decimal Odds`
- Profit on $100 bet: (Decimal Odds - 1) × $100

### Fractional Odds (UK/Ireland)
- 2/3 (equivalent to -150 American)
- 13/10 (equivalent to +130 American)

---

## 3. BET TYPES EXPLAINED

### Moneyline
Bet on who wins outright. No spread involved.
- Best for: Hockey, baseball, soccer (lower-scoring sports where spreads are less meaningful)
- Danger: Heavy juice on big favorites. A -400 favorite only needs to win 80% of the time to break even — juice eats profit fast

### Point Spread (ATS)
The sportsbook gives one team a head start of X points.
- Favorite: -3 (must win by more than 3)
- Underdog: +3 (can lose by up to 2 and still cover, or win outright)
- Standard juice: -110 on both sides
- **Key numbers in NFL: 3 and 7** (see Section 10)

### Totals (Over/Under)
Bet on whether the combined score will be Over or Under a set number.
- Standard juice: -110 on both sides
- Affected by: weather, injuries to key offensive players, pace of play, back-to-back fatigue

### Props (Proposition Bets)
- **Player props:** Player rushing yards over 74.5, QB passing TDs over 1.5, etc.
- **Game props:** First team to score, largest lead, etc.
- Props carry **higher vig** (typically 8-12%) than sides/totals
- Also: significant edges available because books price them less precisely

### Parlays
Multiple bets combined into one ticket. ALL legs must win.
- Payout: odds multiply (e.g., two -110 bets combined = roughly +260)
- Sportsbooks love parlays — they significantly increase hold percentage
- **Two-team parlay break-even:** Need to hit 73.2% with -110 lines
- Parlays should be used sparingly by professional operations

### Teasers
A parlay where you adjust spreads in your favor by buying extra points.
- Standard: 6-point NFL teaser = cross through 3 and 7 = significant value
- **"Wong Teasers"** (crossing 3 and 7 in NFL): statistically profitable historically
- Cost: reduced payout compared to standard parlay

### Futures
Long-term bets placed before a season or event:
- Super Bowl winner, NBA champion, World Series winner
- **Hold percentage on futures is very high (15-30%)** — books shade prices aggressively
- Value exists early in season or when public narrative creates inflated lines

### Live Betting (In-Game)
Wagering on updated lines during a game.
- Books update lines in milliseconds using algorithmic pricing
- Human bettors have brief windows when live lines lag reality
- Reinforcement learning models are most effective here
- High volume opportunity for bots

### Same-Game Parlays (SGPs)
Correlated props bundled into one ticket within a single game.
- Books profit enormously on SGPs — effective vig exceeds 15%
- Avoid as a professional play; use only as entertainment product understanding

---

## 4. THE VIG, JUICE & IMPLIED PROBABILITY

### What Is Vig?
Vigorish (vig, juice) is the commission a sportsbook charges. It's baked into the odds.

**Standard point spread:** -110/-110
- Bettor must risk $110 to win $100
- If equal action both sides: Book collects $220, pays $210 to winner → $10 profit regardless of outcome

### Calculating Vig
For a -110/-110 market:
- Implied prob each side: 110/210 = **52.38%**
- Combined: 104.76% (4.76% total overround / vig)
- True breakeven: Need to win **52.38%** of bets just to break even at -110

### Vig by Market Type
| Market | Typical Vig |
|--------|------------|
| NFL/NBA Sides & Totals (sharp books) | ~4.5-5% |
| MLB Moneylines | 4-6% |
| Player Props | 8-12% |
| Same-Game Parlays | 15%+ |
| Super Bowl Futures | 15-30% |
| Parlays (standard) | Scales with legs added |

### Why Vig Matters Long-Term
At -110 standard juice, a bettor winning 53% of bets is profitable.
At -115 juice (common at soft books), that break-even jumps to ~53.5%.

**The difference between -110 and -115 is worth roughly 1% ROI over a season of bets.** This is why line shopping matters — getting a half-point of value or a nickel of juice can turn a losing bettor into a winning one.

---

## 5. HOW SPORTSBOOKS SET LINES

### Power Ratings
Oddsmakers maintain **power ratings** — numerical rankings of every team's strength. To generate a spread:
1. Take the difference in power ratings between two teams
2. Add or subtract home field advantage (typically 2.5-3 points NFL, 2-3 points NBA, 0.1-0.2 goals soccer)
3. Adjust for injuries, rest, weather, travel

### The Opening Line Process
1. **Market makers** (e.g., Circa, Pinnacle) post the first line with low limits ($500-$2,000)
2. Sharp bettors immediately stress-test these lines
3. Lines move quickly based on early sharp action
4. Other sportsbooks copy or follow the market maker's line
5. As game time approaches, public action and breaking news (injuries) cause further movement

### Why Books Aren't Always Trying to Balance Action
Sophisticated books (Pinnacle, circa) are **sharp-book** operators — they accept sharp action and move lines to find the "true" price. They're essentially outsourcing their modeling to the sharpest bettors.

Soft books target the **public bettor** and may intentionally shade lines toward popular teams to maximize hold from recreational money.

### Line Movement Signals
- **Early movement (low limits):** Usually sharp action from professional syndicates
- **Late movement (high limits):** Could be sharp, could be public, or reactive to injury news
- **No movement despite heavy public action:** Book comfortable with their line; may be shading toward sharp side
- **Reverse Line Movement (RLM):** Line moves against the majority of bets — almost always sharp money

---

## 6. PROFESSIONAL BETTING STRATEGIES

### Value Betting — The Foundation
A bet has **value** when your estimated probability exceeds the implied probability from the odds.

**Example:**
- You believe Team A has a 55% chance to win
- Odds on Team A are -115 → implied probability = 53.5%
- 55% > 53.5% → **value bet**

Value doesn't guarantee a win on any single bet. Over hundreds of bets, positive expected value (+EV) bets produce profits.

**Formula:** `Expected Value = (Prob of Win × Profit) - (Prob of Loss × Stake)`

### Line Shopping — The Most Underrated Edge
Getting the best available price on every bet you make. Requires accounts at multiple books.

**Impact:** The difference between -110 and -105 on a $100 bet is $4.76 per $100 wagered. Over 500 bets per year, that's $2,380 saved from juice reduction alone — before accounting for better prices on spreads and moneylines.

**Action:** Always have accounts at: DraftKings, FanDuel, BetMGM, Caesars, ESPN Bet, PointsBet, and state-specific books. Use OddsShopper or OddsJam to compare lines instantly.

### Specialization
Professional bettors who try to bet everything lose their edge. The sharper you go in one sport or conference, the more your model can generate genuine edges.

**Recommendation for DaftKings staff:** Each analyst should specialize in 1-2 leagues before expanding.

### Timing Bets Strategically
- **"Bet favorites early, underdogs late"** — A well-documented principle
- Favorites attract public money late, which inflates their price over time
- Underdogs often get better prices late as public piles on favorites
- Exception: breaking injury news can flip this logic

### Situational Betting (The "Angle" Approach)
Historical data reveals that certain situations produce consistent ATS edges:

**NFL Situational Angles:**
- Teams off a bye week historically perform better ATS
- Short-week teams (Thursday games) on the road underperform
- Teams coming off a blowout loss often cover the following week ("bounce-back" effect)
- Divisional games are tighter — totals tend to go Under

**NBA Situational Angles:**
- Second night of back-to-backs: Under hits at higher rate
- Teams with 4+ games in 7 days: fatigue suppresses scoring
- Road heavy schedule: performance drops vs. spread

**MLB Situational Angles:**
- Starting pitcher going on extra rest vs. normal rest: performance mixed, but monitor
- First 5 innings (F5) isolates pitcher quality, eliminating bullpen variance
- Park factors are critical for totals — Colorado (Coors Field) inflates run totals significantly

### Don't Chase Losses
"Chasing losses is the single fastest way to go broke." — Universal professional consensus

Set a daily/weekly stop-loss limit and adhere strictly. Emotional decision-making after losses leads to overbetting and irrational selections.

---

## 7. BANKROLL MANAGEMENT

### The Kelly Criterion
Developed by John Kelly (Bell Labs) in 1956. It is the mathematically optimal bet-sizing formula to maximize long-term bankroll growth.

**Formula:**
```
Kelly % = (bp - q) / b

Where:
  b = net fractional odds (e.g., -110 line → b = 100/110 = 0.909)
  p = estimated probability of winning
  q = 1 - p (probability of losing)
```

**Example:**
- Team A: estimated 55% win probability
- Odds: -110 (b = 0.909)
- Kelly % = (0.909 × 0.55 - 0.45) / 0.909 = (0.500 - 0.45) / 0.909 = **5.5%**

This means bet 5.5% of your bankroll on this play.

### Fractional Kelly (What Professionals Actually Use)
Full Kelly is mathematically optimal but produces massive swings that are psychologically difficult to sustain. Professionals use:

| Kelly Fraction | Bankroll Volatility | Use Case |
|----------------|--------------------|--------------------|
| Full Kelly | Very High | Theoretical maximum — rarely used |
| Half Kelly (1/2) | High | Aggressive professionals |
| Quarter Kelly (1/4) | Moderate | Most professional operations |
| Eighth Kelly (1/8) | Low | Conservative, high-volume models |

**Rule of thumb:** Most professional operations bet no more than **2-5% of bankroll per wager**. Flat betting 1-3 units is common for handicappers selling picks.

### Why Kelly Requires Accurate Probability Estimates
Kelly only works if your probability estimates are accurate. If you overestimate your edge, you overbetour and risk of ruin increases dramatically. This is why model calibration and honest record-keeping are critical.

### Unit System for Staff Tracking
Use a standardized unit system:
- 1 unit = 1% of total bankroll
- Standard bet: 1-3 units
- High-confidence bet: 4-5 units (max)
- Never exceed 5% on any single bet

### Record Keeping Requirements
Every bet must be logged:
- Date, sport, league, game
- Bet type (spread, ML, total, prop)
- Line obtained vs. closing line (to track CLV)
- Units bet
- Result (W/L/P) and P&L in units
- Running bankroll and ROI %

Suggested tool: Spreadsheet with auto-calculated ROI, CLV tracking, and performance by sport/bet type.

---

## 8. SHARP VS. PUBLIC MONEY

### Who Are the Sharps?
Sharp bettors are professional, data-driven players:
- Bet large amounts ($5,000-$100,000+ per game)
- Have sophisticated statistical models
- Bet early to get the best price
- Are often limited or banned by soft sportsbooks
- Consistently beat the closing line

### Who Are the Squares?
Square (public) bettors are recreational players:
- Bet small amounts based on emotion, media narrative, team loyalty
- Bet late (day of game)
- Favor popular teams, home favorites, high-scoring games (Overs)
- Predictably bet: NFL favorites on national TV, big market NBA teams, championship-contending MLB teams

### How to Identify Sharp Action

**Bet % vs. Money %:**
If 70% of tickets are on Team A, but only 40% of the money wagered is on Team A, that means Team B is getting larger bets — almost certainly from sharps.

**Reverse Line Movement (RLM):**
If 70% of bets are on Team A, but the line MOVES toward Team A (making them less attractive), the book is protecting itself against sharp action on Team B — the public is paying for Team A but sharp money is on Team B.

**Steam Moves:**
Rapid line movement across multiple books simultaneously. Coordinated sharp syndicates place large bets at multiple books. Lines can move 1-2 points in minutes.

### The "Follow the Sharp" Strategy
When you identify RLM + heavy public percentage on one side:
1. Note which side public is betting (Team A)
2. Confirm line is moving toward Team A (RLM)
3. Bet Team B — the sharp side

**Caveats:**
- Not all RLM is sharp — books sometimes shade lines for positioning
- Late RLM (day of game) is more reliable than early-week RLM
- Must combine with your own analysis — RLM alone is insufficient

### Data Sources for Sharp/Public Splits
- **Action Network** — Public bet percentage and money percentage
- **Sports Insights** — Historical betting database with sharp move alerts
- **OddsJam** — Real-time line movement across 100+ books

---

## 9. CLOSING LINE VALUE (CLV)

### What Is CLV?
**Closing Line Value** is the single best metric for evaluating whether you are a long-term winning bettor.

CLV = the difference between your bet price and the closing price.

**Positive CLV:** You bet at a better price than where the line closed.
**Negative CLV:** You bet at a worse price than where the line closed.

### Why CLV Matters More Than Win Rate
- Variance in sports betting is enormous — even great bettors lose often
- W/L records are misleading over small samples
- If you consistently get positive CLV, you are betting on the "correct" side before the market adjusts — this is the definition of having an edge
- CLV predicts long-term profitability better than actual results

### Example
- You bet Chiefs -3 on Monday
- Line closes at Chiefs -4.5
- You have **+1.5 points of CLV** — you beat the market by 1.5 points
- Even if the Chiefs win by 3 (and you lose the bet), this was a good bet

### Tracking CLV
For every bet, record:
1. Your bet price (spread/odds at time of bet)
2. The official closing price (15 minutes before game)
3. The difference = your CLV

Target: average **positive CLV** across all bets. Professional bettors typically average +0.5 to +2 points of CLV per NFL game bet.

### Tools
- **Unabated CLV Calculator:** https://unabated.com/betting-calculators/closing-line-value-calculator
- **OddsJam:** Tracks CLV historically across all markets
- Manual tracking in Excel works too — just capture opening odds, your odds, and closing odds

---

## 10. NFL — DATA, TRENDS & STRATEGY

### Season Structure
- 18-week regular season (September through early January)
- 14 teams make playoffs; Super Bowl in February
- Betting lines available: Sunday/Monday for following week's games
- Highest betting volume sport in the US by far

### Key Numbers (CRITICAL for NFL Betting)
NFL scoring is based on field goals (3 pts) and touchdowns+PAT (7 pts). This creates "key numbers" — the most common margins of victory:

| Key Number | Frequency | Notes |
|-----------|-----------|-------|
| 3 | ~15% of games | Most common — field goal |
| 7 | ~9% of games | Touchdown + PAT |
| 10 | ~5% | FG + TD |
| 6 | ~5% | Two field goals |
| 4 | ~4% | Rough estimate |
| 14 | ~4% | Two TDs |

**Implication:** When a spread is 3 or 7, it's the most important number to shop. Getting -2.5 vs. -3 can be the difference between winning and pushing. Buying off or onto 3 or 7 is worth paying -130 juice to do.

### ATS Historical Records

**Underdogs vs. Favorites:**
- Road underdogs historically cover ATS at **~53.72%** (2006-2021)
- Home underdogs cover at **~48.62%**
- Favorites cover slightly above 50% overall

**Why Underdogs Cover So Often:**
- Public money inflates favorite lines beyond true probability
- Sportsbooks shade favorites knowing public overweights them
- Creates consistent underdog value

### Situational Trends (Research-Backed)
- **Post-bye week:** Teams fresh off a bye go 55%+ ATS historically
- **Short week (Thursday games):** Road teams on TNF are historically disadvantaged
- **Divisional games:** Scores are closer; Unders hit at higher rate in divisional matchups
- **Back-to-back seasons of success:** Year 2 after a Super Bowl run historically underperforms (SB hangover)
- **Weather:** Wind >15 mph significantly suppresses passing — Unders hit more often. Use weather APIs.
- **Dome teams outdoors in bad weather:** Dome teams struggle significantly against the spread in cold, outdoor environments

### Totals Strategy
- Average NFL total: ~43-47 points
- Weather affects totals more than any other factor
- Track: wind speed, temperature, precipitation probability
- Rule of thumb: >15 mph wind = lean Under, subtract ~2-3 points from expected total

### Key Data Resources for NFL
- EVAnalytics: https://evanalytics.com/nfl/stats/spread
- NxtBets archive: https://nxtbets.com/nfl-betting-trends-archive/
- TeamRankings ATS: https://teamrankings.com/nfl/trends/ats_trends/
- ATS Stats: https://atsstats.com/nfl-picks/
- Sharp Football Analysis: https://sharpfootballanalysis.com (CLV focus)

---

## 11. NBA — DATA, TRENDS & STRATEGY

### Season Structure
- 82-game regular season (October through mid-April)
- 16 teams make playoffs (play-in tournament)
- Extremely high game frequency = lots of data = fast-efficient markets

### Over/Under Historical Data
- Since 2003: **Under 50.3%, Over 49.7%** — nearly a coin flip overall
- Last 5 years: Over has hit at 50.3% — slight uptick
- Only 10 teams above 50% for Overs since 2003; 8 of those are Western Conference teams

### Situational Trends (Critical for NBA)

**Back-to-Back Games:**
- Teams playing their second game in two nights are statistically disadvantaged both ATS and in totals
- Second night of B2B: Under hits at elevated rate — fatigue slows pace
- Road team on second night of B2B: disadvantage compounds

**Schedule Fatigue:**
- 4+ games in 7 days: statistically significant performance drop
- Track "rest differential" — team with more rest days historically outperforms

**Home Court:**
- Historically worth ~3-4 points in NBA
- Post-COVID, home court advantage has diminished slightly
- Large arenas with elite fan bases (Boston, Denver altitude) maintain advantage

### Market Efficiency Notes
- NBA is a highly efficient betting market — lines are set accurately by sharp books
- Best opportunities often found in player props, which are priced less efficiently
- First-half and quarter bets can offer value when sharp books don't adjust as quickly
- Early-season games have more pricing errors because teams haven't established patterns

### Line Timing
- NBA lines posted day before game or morning of
- Sharp action typically early; recreational money comes in closer to tip-off
- First-half lines often lag main line in efficiency

### Key Data Resources for NBA
- Kaggle NBA dataset: https://kaggle.com/datasets/ehallmar/nba-historical-stats-and-betting-data
- EVAnalytics: https://evanalytics.com/nba/stats/spread
- RotoWire archive: https://rotowire.com/betting/nba/archive.php
- NBA.com NBaBet: https://nba.com/nbabet/what-percent-of-nba-games-go-over-the-total
- SportsbookReviewsOnline: https://sportsbookreviewsonline.com/scoresoddsarchives/nba/nbaoddsarchives.htm

---

## 12. MLB — DATA, TRENDS & STRATEGY

### Season Structure
- 162-game regular season (late March through early October)
- No point spread — moneyline is primary bet type
- Run line (+/- 1.5) is baseball's equivalent of spread
- First 5 Innings (F5) is a popular alternate market

### Why MLB is Unique

**Starting Pitcher Dominance:**
The starting pitcher is the single most important variable in any MLB game. When betting moneylines, you are largely betting on the starting pitcher matchup. Key metrics:
- ERA (Earned Run Average)
- WHIP (Walks + Hits per Inning Pitched)
- FIP (Fielding Independent Pitching) — ERA regressed for defense
- K/9 and BB/9 (strikeouts and walks per 9 innings)
- Recent form (last 3 starts)
- Performance vs. specific opponent

**Run Line Strategy (+/- 1.5):**
- Large favorites can often be bet at run line (-1.5) for reduced juice vs. moneyline
- Example: -200 moneyline vs. -130 run line — if you think team wins comfortably, run line is value
- Underdogs on +1.5 run line at big odds offer value in games where they may lose narrowly

**First 5 Innings (F5):**
Eliminates bullpen variance. If you're confident in a starting pitcher matchup, F5 isolates their performance:
- Heavy aces: F5 favorites carry more value vs. moneyline
- Ground ball pitchers vs. fly ball teams: tactical F5 angles

### Park Factors (Critical for Totals)
Every MLB park has unique dimensions and environmental characteristics:

| Park | Avg Run Factor | Notes |
|------|----------------|-------|
| Coors Field (COL) | ~1.25 (inflated) | High altitude, thin air, ball travels further |
| Globe Life Field (TEX) | ~1.05 | Hitter-friendly, climate controlled |
| Oracle Park (SF) | ~0.95 | Cold bay breezes, pitcher-friendly |
| Petco Park (SD) | ~0.93 | Marine layer, pitcher-friendly |
| Yankee Stadium | ~1.08 | Short porch in right field, HR-friendly |
| Kauffman Stadium (KC) | ~0.97 | Large outfield, pitcher-friendly |

**Key:** Always factor park when betting totals. Always check wind speed and direction (particularly at Wrigley Field, where wind blowing out = significantly inflated totals).

### Historical Data Available
- Full MLB historical odds 2010-2021: https://sports-statistics.com/sports-data/mlb-historical-odds-scores-datasets/
- Odds Shark MLB Database: https://oddsshark.com/mlb/database
- EVAnalytics: https://evanalytics.com/mlb/stats/run-line
- StatSharp: https://statsharp.com/mlb/mlb-baseball-betting-stats/

### Weather Tools for MLB
- Weather.com — Wind direction and speed at specific ballparks
- Rotoguru wind tool — Specifically tracks wind at Wrigley and Coors
- Key threshold: 10+ mph winds blowing OUT at Wrigley = add ~1 run to total

---

## 13. NHL — DATA, TRENDS & STRATEGY

### Season Structure
- 82-game regular season (October through April)
- Puck Line (+/- 1.5 goals) is hockey's spread
- Moneyline is the most popular bet type
- High game frequency (multiple games per night)

### Puck Line Analysis
- Unlike baseball run line, puck line in NHL is extremely common (low-scoring sport)
- Favorites on puck line (-1.5): Must win by 2+
- Underdogs on puck line (+1.5): Can lose by 1 or win outright
- **Key finding:** Road underdogs consistently outperform against the puck line
- Home favorites on puck line have historically underperformed

### Totals Trends (2025-2026)
- Games with totals set at **6.5+** have leaned Over this season
- Games with totals at **5.5-6.0** have trended Under
- Overall: Overs hitting at ~52% (up from 49% last season)
- Increase driven by: higher scoring rates and power play efficiency improvements

### Situational Factors

**Back-to-Back Games:**
- B2B is significant in NHL — 82 games in 6 months means fatigue is constant
- Back-to-back games push totals Under — fatigue suppresses offense
- B2B road team at a disadvantage: historically underperforms ATS

**Home Ice:**
- Home teams have a modest advantage in NHL compared to other sports
- But road underdogs provide more consistent value overall

**Goalie Matchups:**
- Starting goalie availability is critical information
- A backup goalie starting changes totals and ML significantly
- Books adjust quickly — get confirmed starting goalies early (typically announced ~90 minutes before puck drop)

### Key Data Resources for NHL
- StatSharp: https://statsharp.com/nhl/nhl-hockey-betting-stats/
- EVAnalytics: https://evanalytics.com/nhl/stats/1p-total
- ATS Stats: https://atsstats.com/nhl-picks/
- OddsTrader: https://oddstrader.com/nhl/standings/
- SportsBettingDime NHL: https://sportsbettingdime.com/nhl/public-betting-trends/

---

## 14. SOCCER — PREMIER LEAGUE & MLS

### Why Soccer Is Unique Compared to US Sports

**The Draw:**
Soccer has three outcomes: Home Win (1), Draw (X), Away Win (2). This is called **1X2 betting** and is the primary market globally. The draw changes the mathematics significantly:
- In a "50/50" game, each side actually has ~35% chance with ~30% draw probability
- Books price this as three-way market — odds are typically longer

**Asian Handicap:**
Eliminates the draw by giving fractional handicaps. Creates two-outcome markets with sharper pricing and lower vig. Most professional soccer bettors prefer Asian Handicap over 1X2.
- Example: Arsenal -0.5 means Arsenal must win (any score); at -1.0, Arsenal must win by 2+
- Half-goal handicaps eliminate the draw possibility

**Over/Under Goals:**
Most common total: 2.5 goals (Over = 3+ goals, Under = 2 or fewer)
Other popular markets: 1.5, 3.5, 4.5

### Premier League
- 38 games per team per season (August through May)
- 20 teams, highest global TV audience
- Highly efficient betting market — sharp global action
- Historical data: Football-Bet-Data covers 20+ years of EPL odds
- Key factor: Squad rotation (especially Champions League weeks)
- Home advantage: Historically worth ~0.4-0.5 goals (Asian Handicap equivalent)

### MLS (Major League Soccer)
- 34 regular season games (February through October)
- Less efficient market than European leagues — more edge available
- Historical odds: OddsWarehouse (2010-2025)
- Dimers simulates every MLS match 10,000 times for predictions
- Important: MLS Eastern/Western Conference travel distances are extreme — travel fatigue is significant
- Higher variance than EPL due to smaller squad depth and market inefficiency

### Data Resources for Soccer
- Football-Bet-Data: https://football-bet-data.com (65+ leagues, historical)
- OddsPortal: https://oddsportal.com (historical results, many leagues)
- OddAlerts downloads: https://oddalerts.com/downloads (CSV downloads, daily updated)
- Kaggle EPL dataset: https://kaggle.com/datasets/thedevastator/uncovering-betting-patterns-in-the-premier-leagu
- OddsWarehouse MLS: https://oddswarehouse.com/products/mls-historical-sports-betting-odds-database
- Dimers MLS: https://dimers.com/bet-hub/mls/schedule

---

## 15. PREDICTION MARKETS — KALSHI & POLYMARKET

### Why Prediction Markets Matter for DaftKings

Prediction markets are a **parallel universe** to traditional sportsbooks. They operate under different regulatory frameworks, have different liquidity characteristics, and in many cases represent a significant edge opportunity — especially for algorithmically-driven operators. As of 2026, these markets are exploding: Bank of America estimates sports event contracts could become a **$1.1 trillion annual market**.

---

### Kalshi

**What It Is:**
Kalshi is the first and only **CFTC-regulated** (Commodity Futures Trading Commission) prediction market exchange in the United States. This is the key distinction: Kalshi is not regulated under state sports betting laws — it operates as a **financial exchange**, not a sportsbook.

**Why This Matters:**
- Available in **all 50 states** (vs. 39 for traditional sportsbooks)
- Regulated federally by the CFTC, not state gaming commissions
- April 2026: Federal appeals court ruled New Jersey gaming regulators cannot regulate Kalshi's sports prediction market — setting the stage for potential Supreme Court review
- 79% of Kalshi's March 2026 trades were in sports markets
- $100 billion in projected contract trades for 2026

**How Contracts Work:**
Rather than placing a "bet," you buy an event contract:
- Each contract is priced from $0.01 to $0.99 (representing 1%-99% probability)
- If correct, the contract pays $1.00
- If incorrect, the contract pays $0.00
- **Example:** "Will the Chiefs win tonight?" at $0.61 = the market implies 61% chance. Buy 100 shares at $0.61 = cost $61. If Chiefs win, you receive $100, profit = $39.

**Fee Structure:**
- 2% fee on debit card/Google Pay deposits
- No fee for bank transfer (ACH)
- Trading fees vary by market type (typically lower than traditional sportsbook vig)

**Sports Coverage:**
NFL, NBA, MLB, NHL, NCAA Football, NCAA Basketball, UFC, European Soccer

**API:**
Kalshi offers a full developer API:
- REST API v2 for market data, order management, account operations
- WebSocket API for real-time streaming (orderbook deltas, ticker updates, trades, fills)
- FIX 4.4 protocol for institutional low-latency trading
- Demo/sandbox environment for testing
- Authentication: RSA key pair (generate in account settings, sign each request)
- Full docs: https://docs.kalshi.com/welcome
- Python guide + demo sandbox: https://agentbets.ai/guides/kalshi-api-guide/

**Real-Time Odds:**
- OpticOdds provides Kalshi API integration: https://opticodds.com/sportsbooks/kalshi-api
- SportsGameOdds Kalshi API: https://sportsgameodds.com/kalshi-odds-api/

---

### Polymarket

**What It Is:**
Polymarket is a decentralized prediction market built on the Polygon blockchain. Users trade yes/no outcome contracts using USDC (a stablecoin). Unlike Kalshi, Polymarket is crypto-native.

**Key Difference vs. Kalshi:**
- Polymarket operates on blockchain — smart contracts settle outcomes
- No centralized operator (decentralized exchange)
- Primarily available for US users via VPN workarounds (check current legal status)
- Far more speculative market with higher volatility

**Polymarket Bot Performance (Real Data from 2025-2026):**
- A Claude-powered bot turned **$1 into $3.3 million** on Polymarket since August 2025
- Another Claude bot converted **$1,000 into $14,216 in 48 hours**
- One bot reportedly turned **$313 into $414,000 in a single month** (Bitcoin/ETH/SOL 15-min markets, $4-5K bets per trade, claimed 98% win rate — likely an outlier)
- A probability model trained on news/social media data generated **$2.2M over two months**, continuously retraining itself on contracts where market pricing diverged from real-world probability

**How Polymarket Bots Make Money:**
1. **Probability Arbitrage** — Find contracts where AI-estimated probability exceeds market price
2. **Correlation Arbitrage** — Exploit mispricings between correlated markets (e.g., "Team A wins division" vs. "Team A wins championship")
3. **Momentum Trading** — Follow early sharp movement and ride price changes
4. **Automated Market Making (AMM)** — Provide liquidity on both sides, capture the spread

**Notable Open-Source Bots (Study These):**
- `dylanpersonguy/Fully-Autonomous-Polymarket-AI-Trading-Bot` — Multi-model ensemble (Claude + GPT-4o + Gemini), 15+ risk checks, fractional Kelly, 9-tab monitoring dashboard
- `kyleskom/NBA-Machine-Learning-Sports-Betting` — XGBoost/neural network for NBA moneyline + totals
- `randomness11/probablyprofit` — AI-powered trading bot framework for Polymarket
- `jakewallin82/NBA-XGBoost` — NBA betting with XGBoost
- `llSourcell/ChatGPT_Sports_Betting_Bot` — ChatGPT sports betting bot reference

---

### Kalshi vs. Traditional Sportsbooks vs. Polymarket

| Factor | Traditional Sportsbook | Kalshi | Polymarket |
|--------|----------------------|--------|------------|
| Regulation | State gaming law | Federal CFTC | Decentralized/blockchain |
| US Availability | 39 states | All 50 states | Restricted/VPN |
| Bet Type | Wager | Event contract (shares) | Blockchain contract |
| Vig/Fee | 4.5-5% standard | Lower (exchange model) | Varies by market |
| API Access | Limited (varies) | Full REST + WebSocket | Full API |
| Bot-Friendly? | Bots get limited/banned | Yes — exchange model | Yes — fully automated |
| Max Bet | Limited for sharps | Market liquidity dependent | Market depth dependent |
| Settlement | Instant | Instant | Smart contract |
| Key Edge | Line shopping, CLV | Market inefficiency | Probability vs. market price |

**Key Takeaway:** Kalshi and Polymarket are **bot-friendly environments** in ways that traditional sportsbooks are not. Sharp bettors at DraftKings and FanDuel get their limits cut. On Kalshi's exchange model, you are trading against other users — there is no book to limit you.

---

## 16. MACHINE LEARNING & BOT DEVELOPMENT

### Overview
Modern sports betting is increasingly dominated by algorithmic bettors. As of 2026, **48% of activity on major betting networks comes from AI-traded bets** (up from 28%). Building a bot is not optional for long-term competitiveness — it's essential.

### Target Performance
- Most sports ML models achieve **55-65% accuracy**
- **55% is enough to be profitable at -110 juice** (break-even is 52.38%)
- Some specialized models exceed 70-80% in niche markets
- Overfitting is the greatest risk — always test on out-of-sample data

### Data Pipeline Architecture

**Inputs (Feature Engineering):**
- Historical game results (scores, spreads, totals, moneylines)
- Team efficiency stats (offensive/defensive ratings)
- Player availability / injury status
- Rest differential (days since last game)
- Travel distance and direction (West-to-East is tougher)
- Home/away status
- Weather data (NFL and MLB totals especially)
- Opening line and current line (for CLV tracking and sharp signal detection)
- Historical ATS records in similar situations
- Betting percentages (public money signal)

**Model Types:**
| Model | Strength | Use Case |
|-------|---------|---------|
| Logistic Regression | Interpretable, fast | Baseline model, spread coverage probability |
| Random Forest | Handles non-linearity, robust | ATS prediction, value detection |
| XGBoost/Gradient Boosting | Best accuracy | General prediction, ensemble methods |
| Neural Networks | Captures complex patterns | Large dataset (NBA/MLB), live betting |
| Reinforcement Learning | Adapts in real-time | Live betting, in-game line exploitation |

### Technology Stack
```
Language: Python
Data: Pandas, NumPy
ML: scikit-learn, XGBoost, PyTorch/TensorFlow
Backtesting: Custom framework or Vectorbt
APIs: The Odds API, SportsDataIO, API-Sports, Kalshi API
Database: PostgreSQL or SQLite for historical storage
Scheduling: Cron jobs or Apache Airflow
Alerting: Telegram bot or Slack webhook for bet alerts
```

### GitHub Reference
- NBA ML Sports Betting (open source): https://github.com/kyleskom/NBA-Machine-Learning-Sports-Betting
- NBA XGBoost: https://github.com/jakewallin82/NBA-XGBoost
- Autonomous Polymarket Bot: https://github.com/dylanpersonguy/Fully-Autonomous-Polymarket-AI-Trading-Bot
- SureBets Arbitrage Bot: https://github.com/TessaRichardson/SureBetsBot
- ChatGPT Sports Betting Bot reference: https://github.com/llSourcell/ChatGPT_Sports_Betting_Bot

### Backtesting Framework Requirements
1. Never backtest on the same data you trained on (data leakage)
2. Use **walk-forward analysis** — train on Year 1-3, test on Year 4, move forward
3. Simulate realistic bet sizing (Kelly or flat) and include juice in results
4. Track CLV of generated picks, not just W/L record
5. Account for line availability — not all prices available at closing line

### AI Landscape in 2026
- DraftKings uses ML for everything from odds pricing to same-game parlay analysis
- AI-traded bets now account for **48% of activity** on major betting networks
- AI-powered live betting is now the fastest-growing segment
- Real-time ML models update odds in milliseconds during live games
- Human bettors have brief windows when live lines lag reality — bot advantage
- Global AI match outcome prediction market: $1.3B (2025) → projected $6.3B (2033)

---

## 17. CLAUDE + MCP BOT STACK (PRODUCTION BLUEPRINT)

### Overview
The most exciting development in sports betting automation for 2026 is the ability to connect Claude directly to live sports odds data using **Model Context Protocol (MCP) servers**. This eliminates the need for separate API wrapper code — Claude can query live odds, analyze value, calculate Kelly sizing, and generate bet recommendations autonomously in a single pipeline.

---

### The Odds API MCP Integration

**What it does:** Connects Claude directly to The Odds API account, giving it real-time odds across 265+ bookmakers via natural language.

**Available Tools (via MCP):**
- `get_sports` — List all in-season sports
- `get_events` — Fetch live and upcoming events for a sport
- `get_odds` — Fetch live odds with bookmaker, region, and market filters
- `get_event_odds` — Retrieve odds for a specific game

**Setup Command (Claude Code):**
```bash
claude mcp add-json "the-odds-api" '{"command":"python","args":["-m","wagyu_sports.mcp_server"]}'
```

**Composio Alternative (easier auth):**
```bash
claude mcp add --transport http the_odds_api-composio "YOUR_MCP_URL" --headers "X-API-Key:YOUR_COMPOSIO_API_KEY"
```

**Resources:**
- Composio integration guide: https://composio.dev/toolkits/the_odds_api/framework/claude-code
- MCP server (Wagyu Sports): https://playbooks.com/mcp/hrgarber-wagyu-sports
- MCP Market listing: https://mcpmarket.com/server/wagyu-sports
- API-Sports MCP via Composio: https://mcp.composio.dev/api_sports

---

### Full Production Bot Architecture

Based on real bots deployed in 2025-2026, here is the complete architecture for a production sports betting / prediction market bot:

```
┌─────────────────────────────────────────────────────────┐
│                    DaftKings Bot v1.0                    │
├─────────────┬──────────────┬──────────────┬─────────────┤
│   SCANNER   │   ANALYZER   │ RISK MANAGER │  EXECUTOR   │
│             │              │              │             │
│ Polls odds  │ Claude + ML  │ Kelly Crit.  │ Places bet  │
│ every 5 min │ evaluates EV │ sizes stake  │ via API     │
│ via MCP/API │ vs. closing  │ kill switch  │ Kalshi/book │
│             │ line model   │ drawdown chk │             │
└─────────────┴──────────────┴──────────────┴─────────────┘
         ↓                                       ↓
  Telegram/Slack Alert                   Log to Database
  (every bet, every error)               (W/L, CLV, P&L)
```

**Component Breakdown:**

**1. Scanner (Data Ingestion)**
- Runs on a cron schedule: every 5 minutes during active markets
- Queries The Odds API or Kalshi API for current lines
- Detects line movement (>0.5 point change = investigate)
- Detects steam moves (rapid movement across multiple books simultaneously)
- Outputs a clean table of all available markets

**2. Analyzer (Claude + ML Model)**
- Claude receives the market data via MCP
- ML model (XGBoost) generates win probability estimates
- Claude compares model probability to implied probability from odds
- Flags bets where model probability exceeds implied probability by threshold (e.g., >3%)
- Analyzes sharp vs. public split (via Sports Insights / Action Network data)
- Checks for reverse line movement
- Outputs: bet recommendation, confidence level, estimated edge

**3. Risk Manager**
- Applies Kelly Criterion (typically Quarter-Kelly) to size the bet
- Checks current bankroll state
- Enforces position limits (max 5% bankroll on any single bet)
- **Kill Switch:** If daily drawdown exceeds -40%, halts all further betting for the day
- Enforces sport-specific limits (e.g., max $X on any single MLB game)
- Checks for correlated bets (e.g., don't bet same team moneyline AND runline)

**4. Executor**
- Places bet via Kalshi API, sportsbook API, or logged for manual execution
- Confirms bet placement and records confirmation ID
- Logs: market, price obtained, size, timestamp

**5. Monitoring & Alerting**
- Telegram or Slack bot sends alert for every placed bet
- Error alerts for API failures, model errors, connection issues
- Weekly performance report: ROI, CLV average, W/L by sport
- Database (PostgreSQL recommended) stores every bet with full metadata

---

### VPS Deployment Guide

Running on your laptop = missed opportunities and downtime. Deploy on a VPS:

**Recommended Providers:**
- **DigitalOcean** — $6-12/month droplet, reliable, fast setup
- **Vultr** — $6/month, good for low-latency needs
- **Hetzner** — European, very cheap (~€4/month), good uptime

**Setup Steps:**
1. Provision Ubuntu 22.04 VPS (minimum 1GB RAM, 1 vCPU)
2. Install Python 3.11+, pip dependencies
3. Clone your bot repository
4. Set up environment variables (API keys, Kalshi credentials)
5. Configure cron job: `*/5 * * * * /usr/bin/python3 /home/user/bot/scanner.py`
6. Set up fail2ban and UFW firewall
7. Configure Telegram bot for alerts
8. Test in dry-run mode 2 weeks before live deployment

**Estimated Monthly Cost:** $10-20/month for a fully operational 24/7 bot

---

### Risk Management Rules (Non-Negotiable)

These rules must be hardcoded in the bot — not optional:

| Rule | Implementation |
|------|----------------|
| Max single bet | 5% of bankroll (hard cap) |
| Daily stop-loss | -40% of daily bankroll → kill switch activates |
| Weekly stop-loss | -20% of starting weekly bankroll → manual review required |
| Minimum edge threshold | Only bet when model edge > 3% (adjustable) |
| Max correlated positions | No more than 3 bets on same team per day |
| Dry run before live | Run 2+ weeks without real money first |
| Log everything | Every decision logged with full reasoning for audit |
| No chasing | Bot cannot increase bet size after consecutive losses |

---

### Dry Run / Paper Trading Protocol

**Before spending real money:**
1. Run bot for minimum **2 weeks in paper trading mode**
2. Record every bet that would have been placed
3. Calculate simulated P&L at actual closing odds
4. Track CLV: are your bot's picks beating the closing line?
5. If average CLV is positive over 100+ bets: proceed to live with small stake
6. If average CLV is negative: model needs retraining

**Critical:** A winning paper-trade record does not guarantee live profits. Market liquidity, bet size impact on odds, and timing all differ in live conditions.

---

### Claude Code + Polymarket Full Workflow Example

Based on real deployments (Medium article by Örvar Karlsson, March 2026):

```python
# Example workflow Claude executes via /loop command every 5 minutes

# 1. Scanner checks open Kalshi sports markets
markets = kalshi_api.get_markets(status="open", category="sports")

# 2. For each market, compare Kalshi price to model estimate
for market in markets:
    model_prob = xgboost_model.predict(market.features)
    market_prob = market.yes_price  # e.g., 0.61 = 61%
    edge = model_prob - market_prob
    
    # 3. If edge > threshold, size the bet
    if edge > 0.03:  # 3% minimum edge
        kelly_fraction = calculate_quarter_kelly(edge, market_prob)
        stake = bankroll * kelly_fraction
        
        # 4. Risk check
        if stake <= MAX_BET and daily_drawdown < 0.40:
            # 5. Execute
            kalshi_api.place_order(market.id, "yes", stake)
            send_telegram_alert(f"BET PLACED: {market.title} | Edge: {edge:.1%} | Stake: ${stake:.0f}")
            log_bet_to_database(market, model_prob, market_prob, stake)
```

---

### Market Mechanics MCP Skill

MCP Market has a **"Market Mechanics & Betting"** Claude skill specifically designed for:
- Calculating Kelly Criterion
- Computing Brier scores (probability calibration metric)
- Calculating edge for prediction markets

Available at: https://mcpmarket.com (search "Market Mechanics")

---

## 18. DATA SOURCES & APIs

### Tier 1 — APIs for Bot Development

**The Odds API** — https://the-odds-api.com
- Historical odds from June 2020+, snapshots every 5 minutes (from Sept 2022)
- Coverage: NFL, NBA, MLB, NHL, soccer, and more
- Free tier available; paid plans for historical and real-time
- Best for: backtesting, real-time line comparison

**OddsJam API** — https://oddsjam.com/odds-api
- Real-time odds including player props and alternate markets
- Complete historical feed with closing lines and live changes
- Best for: props, alternate markets, CLV tracking

**SportsDataIO** — https://sportsdata.io
- Live scores, odds, projections, player stats, injuries
- NFL, NBA, MLB, NHL, NCAA all covered
- Best for: live data feeds and player-level data integration

**API-Sports** — https://api-sports.io
- 2,000+ competitions, 15+ years of historical data
- Real-time updates every 15 seconds
- Best for: international sports, soccer coverage

**Tx Lab (TxODDS)** — https://txodds.net
- 800+ bookmakers in database
- 5M+ fixtures, decades of history
- REST & WebSocket APIs
- Best for: maximum bookmaker coverage and deep history

### Tier 2 — Free/Low-Cost Historical Archives

| Source | Sports | Time Range | URL |
|--------|--------|-----------|-----|
| Sports-Statistics.com | MLB | 2010-2021 | https://sports-statistics.com |
| SportsbookReviewsOnline | All major | 2000s+ | https://sportsbookreviewsonline.com |
| Kaggle NBA Dataset | NBA | 2003+ | Kaggle search "NBA betting" |
| Odds Shark Database | MLB/NBA/NFL/NHL | 2000s+ | https://oddsshark.com |
| OddsWarehouse | MLS | 2010-2025 | https://oddswarehouse.com |
| Football-Bet-Data | Soccer (65+ leagues) | 2000s+ | https://football-bet-data.com |
| OddAlerts | Soccer | Current | https://oddalerts.com/downloads |

### Tier 3 — Analytics Platforms for Staff Research

| Platform | Strength | URL |
|----------|---------|-----|
| TeamRankings / BetIQ | Situational ATS trends | https://teamrankings.com |
| EVAnalytics | ATS/totals by sport and situation | https://evanalytics.com |
| StatSharp | MLB/NFL/NHL/NBA records | https://statsharp.com |
| Action Network | Sharp/public tracking | https://actionnetwork.com |
| Sports Insights | Historical betting database | https://sportsinsights.com |
| Unabated | CLV tools, line comparison | https://unabated.com |
| OddsShopper | Line shopping interface | https://oddsshopper.com |
| ATS Stats | Daily market grades | https://atsstats.com |

---

## 19. LEGAL LANDSCAPE (US)

### History
- **May 14, 2018:** US Supreme Court struck down PASPA (Professional and Amateur Sports Protection Act) in Murphy v. NCAA
- This gave each state the right to legalize sports betting independently
- Before 2018: Only Nevada had full legal sports betting

### Current Status (April 2026)
- **39 states + Washington DC** have some form of legal sports betting
- Mobile (online) betting is not legal everywhere — some states restrict to retail only
- **States without legal sports betting:** California, Texas, Idaho, Utah, Minnesota, Alabama, Georgia, South Carolina, Oklahoma, Alaska, Hawaii
- Hawaii and Utah prohibit ALL forms of gambling (constitutional bans)
- California and Texas are the two biggest outstanding markets — both have failed ballot measures/legislation repeatedly

### Age Requirements
- Most states: **21+**
- A small number allow 18+ in limited circumstances (typically retail/lottery-operated)

### Regulatory Bodies by State (Examples)
- New York: New York State Gaming Commission
- New Jersey: Division of Gaming Enforcement
- Illinois: Illinois Gaming Board
- Colorado: Colorado Division of Gaming
- Pennsylvania: Pennsylvania Gaming Control Board

### Tax Treatment
- Winnings are taxable income in the United States
- Sportsbooks must report winnings over $600 (or winnings that are 300x the wager)
- Form W-2G issued by books for large payouts
- Professional bettors can deduct losses against winnings as a business expense
- Consult a CPA with gambling experience for entity structure

### Market Size Reference
- US handle 2023: $121 billion
- New York: $19B | New Jersey: $11.9B | Illinois: $11.6B | Pennsylvania: $7.6B

### Kalshi Legal Status (NEW — April 2026)
- Kalshi operates under **federal CFTC jurisdiction** (Commodity Futures Trading Commission), NOT state gaming laws
- April 2026: Third Circuit federal appeals court ruled New Jersey cannot regulate Kalshi's sports prediction markets
- This means Kalshi is available in **all 50 states**, including California, Texas, and other states where traditional sports betting is illegal
- 19 federal lawsuits against Kalshi remain active from state gaming regulators
- US Supreme Court review possible — this is the most significant legal development in sports betting since PASPA repeal
- Bank of America projects sports event contracts could be a **$1.1 trillion annual market**

### Regulatory Distinction: Sportsbook vs. Prediction Market
| | Traditional Sportsbook | Kalshi |
|--|----------------------|--------|
| Regulator | State gaming commission | CFTC (federal) |
| Legal in | 39 states + DC | All 50 states (as of 2026) |
| Bet limits | Can limit sharp bettors | Exchange model — no limit |
| Tax reporting | W-2G for large wins | Consult CPA for event contracts |

---

## 20. GLOSSARY

| Term | Definition |
|------|-----------|
| ATS | Against the Spread — whether a team covered the point spread |
| Asian Handicap | Soccer-specific handicap that eliminates the draw |
| Backdoor Cover | A team covers the spread late in a game with a meaningless score |
| Beard | Someone who places bets on behalf of a sharp who has been limited |
| Book (Sportsbook) | Entity that accepts sports wagers |
| CLV | Closing Line Value — your price vs. closing price |
| Consensus | Aggregate public betting percentage across books |
| Cover | When a team beats the point spread |
| Dead Heat | Multiple selections tie; payout is prorated |
| Edge | A statistical advantage over the market |
| EV (Expected Value) | The mathematical expectation of profit from a bet |
| F5 | First 5 Innings — MLB alternate market |
| FIP | Fielding Independent Pitching — MLB stat removing defensive influence |
| Futures | Long-term bets on season outcomes (champion, MVP, etc.) |
| Handle | Total dollars wagered on a market |
| Handicapper | Someone who analyzes games and predicts ATS outcomes |
| Hold | Sportsbook's profit margin (handle minus payouts) |
| Hook | Half-point in a spread (e.g., -3.5 = "three and a hook") |
| Juice | See Vig |
| Kelly Criterion | Optimal bet-sizing formula based on edge and probability |
| Key Number | Most common margin of victory (NFL: 3 and 7) |
| Layoff | When a book bets at another book to balance exposure |
| Limit | Maximum bet a book accepts from a given bettor |
| Live Betting | Wagering during a game on real-time updated lines |
| Middling | Betting both sides of a game at different numbers to win both |
| Moneyline | Straight bet on who wins with no point spread |
| No Action | A bet that is voided and returns the stake (injury scratches, weather) |
| Odds | The price of a bet expressed in various formats |
| Opening Line | First odds posted for an event |
| Closing Line | Final odds posted immediately before the event starts |
| Overlay | When the true probability is higher than the implied probability |
| Parlay | Multiple bets combined — all legs must win |
| Pick'em | Game with no spread; moneyline applies |
| Power Rating | Numerical ranking of team strength used to generate spreads |
| Prop | Proposition bet on specific outcomes within a game |
| Puck Line | NHL's point spread (+/- 1.5 goals) |
| Push | A tie result where the spread lands exactly on the number; bets refunded |
| Reverse Line Movement (RLM) | Line moves opposite to majority of public bets — sharp signal |
| ROI | Return on Investment — net profit divided by total wagered |
| Run Line | MLB's point spread (+/- 1.5 runs) |
| Same-Game Parlay (SGP) | Correlated props on a single game combined into one bet |
| Sharp | Professional, data-driven bettor |
| Square | Casual, recreational bettor |
| Steam | Rapid simultaneous line movement from coordinated sharp action |
| Syndicate | Organized group of sharp bettors pooling capital and models |
| Teaser | Parlay with points added in your favor in exchange for lower payout |
| Totals | Over/Under bet on combined score |
| Unit | Standard bet size (typically 1-3% of bankroll) |
| Vig (Vigorish) | Sportsbook's commission, built into the odds |
| Value Bet | Bet where your probability estimate exceeds implied probability |
| Wiseguy | Synonym for sharp bettor |
| Wong Teaser | 6-point NFL teaser that crosses through both 3 and 7 |

---

*Document compiled April 2026 for DaftKings staff training. Version 2.0 adds Kalshi/Polymarket prediction markets, Claude MCP bot architecture, and full production deployment blueprint. Update quarterly with new historical data and regulatory changes.*
