# DaftKings — Project Intelligence for Claude

## Project Purpose
This project is a **sports betting company training system** being built by Mike. The goal is to:
1. Train staff on every aspect of professional sports betting
2. Build a comprehensive knowledge base with historical data across all major leagues
3. Eventually develop an automated betting bot

Claude should always operate in the context of building a professional, legally-operated sports betting business. All responses should be educational, data-driven, and aimed at developing a highly skilled team.

---

## Company Vision
- **Company Name:** DaftKings (working name)
- **Owner:** Mike (fructifyme@gmail.com)
- **Stage:** Training phase → Bot development
- **Model:** Legal, regulated sports betting operation
- **Staff Training Goal:** Team must understand betting fundamentals, analytics, league-specific trends, bankroll management, and market dynamics

---

## Leagues in Scope (Primary)
| League | Sport | Season |
|--------|-------|--------|
| NFL | American Football | Sep–Feb |
| NBA | Basketball | Oct–Jun |
| MLB | Baseball | Mar–Oct |
| NHL | Ice Hockey | Oct–Jun |
| Premier League | Soccer | Aug–May |
| MLS | Soccer | Feb–Nov |
| NCAA Football | College Football | Aug–Jan |
| NCAA Basketball | College Basketball | Nov–Apr |

---

## Core Training Topics

### 1. Betting Fundamentals
- Moneyline, Point Spread, Totals (Over/Under)
- Props, Parlays, Teasers, Futures, Live Betting
- Odds formats: American (+/-), Decimal, Fractional
- Vig/Juice and Implied Probability
- How sportsbooks set and move lines
- Key numbers by sport

### 2. Professional Strategies
- Value Betting (finding mispriced odds)
- Closing Line Value (CLV) — the #1 long-term success metric
- Line Shopping (using multiple books)
- Sharp money vs. public money
- Reverse Line Movement (RLM)
- Specialization (pick 1-2 leagues to master)
- Timing bets (early vs. late action)

### 3. Bankroll Management
- Kelly Criterion (full, half, quarter Kelly)
- Unit sizing (1-5% per bet rule)
- Record keeping & tracking ROI
- Avoiding chasing losses

### 4. Market Dynamics
- How oddsmakers use power ratings
- Opening lines vs. closing lines
- Steam moves and sharp action
- Public betting percentages and handle %
- Consensus percentages and their limits

### 5. Data & Analytics
- Historical ATS (against the spread) records
- Situational trends (home/away, favorite/underdog, rest/fatigue)
- Injury impact modeling
- Weather and environmental factors (NFL, MLB, College)
- Back-to-back performance (NBA, NHL)
- Travel fatigue factors

### 6. Bot Development (Future Phase)
- Data ingestion: APIs (The Odds API, OddsJam, SportsDataIO, API-Sports)
- Feature engineering: team stats, player props, weather, injury data
- ML models: regression, random forests, neural networks
- Backtesting frameworks
- Live betting automation
- Risk management logic

---

## Key Resources & Data Sources

### Odds & Historical Data
- **The Odds API** — https://the-odds-api.com (historical odds from 2020+, 5-min snapshots from 2022)
- **OddsJam API** — https://oddsjam.com/odds-api (real-time + historical, props coverage)
- **SportsDataIO** — https://sportsdata.io (live stats, odds, projections across NFL/NBA/MLB/NHL)
- **API-Sports** — https://api-sports.io (2,000+ competitions, 15+ years historical)
- **EVAnalytics** — https://evanalytics.com (ATS/totals breakdowns by sport)
- **Sports-Statistics.com** — https://sports-statistics.com (MLB/NFL historical odds datasets 2010-2021)
- **Kaggle: NBA Historical Betting Data** — https://www.kaggle.com/datasets/ehallmar/nba-historical-stats-and-betting-data
- **Odds Shark Database** — https://www.oddsshark.com (MLB/NBA/NFL/NHL historical)
- **OddsWarehouse** — https://www.oddswarehouse.com (MLS historical 2010-2025)
- **Football-Bet-Data** — https://www.football-bet-data.com (65+ soccer leagues)
- **SportsbookReviewsOnline** — https://www.sportsbookreviewsonline.com/scoresoddsarchives (free archives)
- **Tx Lab** — https://txodds.net (800+ bookmakers, 5M+ fixtures, decades of history)

### Analytics & Trend Platforms
- **TeamRankings / BetIQ** — https://teamrankings.com / https://betiq.teamrankings.com
- **EVAnalytics** — https://evanalytics.com
- **StatSharp** — https://statsharp.com
- **StatRankings** — https://statrankings.com
- **ATS Stats** — https://atsstats.com
- **Sports Insights** — https://sportsinsights.com
- **Action Network** — https://actionnetwork.com
- **OddsShopper** — https://oddsshopper.com
- **Unabated** — https://unabated.com

### Sharp Money Tracking
- **Sports Insights** — bet % vs. money % tracking
- **Action Network** — public betting percentages
- **BetIQ (TeamRankings)** — sharp vs. public splits

---

## Key League-Specific Facts for Staff Training

### NFL
- Most important key numbers: **3** (field goal, ~15% of games) and **7** (TD+PAT, ~9%)
- Also watch: 10, 6, 4, 14
- Road underdogs historically cover ATS at ~53.72% (2006–2021)
- Home underdogs cover at ~48.62% — less profitable
- Line typically opens Sunday/Monday for next week's games
- "Bet favorites early, underdogs late" — classic timing rule
- Weather matters significantly for totals (wind, cold, precipitation)

### NBA
- Over/Under near coin flip historically: Under 50.3%, Over 49.7% (since 2003)
- Back-to-back situations are critical — fatigue suppresses scoring and spread coverage
- Home court advantage has been shrinking post-COVID
- Western Conference teams historically lean more Over than Eastern teams

### MLB
- Run line = baseball's point spread (+/- 1.5 runs)
- Moneyline is primary bet type — heavy juice on big favorites
- Pitcher matchup is the single most important variable
- Weather (wind, temperature, park factors) heavily influence totals
- First 5 innings (F5) bets isolate starting pitcher performance
- Data available: 2010–2021 historical run lines, moneylines, and totals

### NHL
- Puck line = hockey's point spread (+/- 1.5 goals)
- Road underdogs provide most consistent value — cover more than home favorites
- Totals set at 6.5+ have leaned Over; 5.5–6 goals lean Under
- Back-to-back situations push games Under (fatigue slows offense)
- Power play efficiency is a key factor in totals modeling

### Premier League / Soccer
- Main markets: 1X2 (home/draw/away), Over/Under 2.5 goals, Asian Handicap
- Historical data available via Football-Bet-Data, OddsPortal for 65+ leagues
- Draw is always a factor — unique to soccer, changes probability math
- Asian handicap eliminates the draw — sharper pricing, smaller margins

### MLS
- Historical data from Odds Warehouse (2010-2025)
- Less efficient market than EPL — more opportunities for sharp bettors
- Home field advantage more pronounced than in European leagues

---

## Bot Development Roadmap (Future Phase)

### Phase 1: Data Infrastructure
- [ ] Set up API connections (The Odds API, SportsDataIO, or OddsJam)
- [ ] Build historical odds database (start with 2+ sports)
- [ ] Ingest team stats, player stats, injury data feeds
- [ ] Weather API integration for NFL/MLB totals

### Phase 2: Model Development
- [ ] Feature engineering (ATS history, rest days, travel, SOS)
- [ ] Baseline models: logistic regression, random forests
- [ ] Backtesting framework (test on out-of-sample historical data)
- [ ] CLV tracking system

### Phase 3: Automation
- [ ] Real-time odds monitoring and alert system
- [ ] Value bet detection (compare model probability vs. implied probability)
- [ ] Bankroll management logic (Kelly Criterion implementation)
- [ ] Live betting module (reinforcement learning consideration)

### Key ML Concepts for the Bot
- **Overfitting risk:** Models that look great on training data often fail in production
- **Target accuracy:** Most sports ML models achieve 55–65% — profitable but not flashy
- **Feature importance:** Closing line value, rest differentials, travel distance, weather
- **Tools:** Python (scikit-learn, XGBoost, PyTorch), Pandas, Jupyter

---

## Legal & Compliance Notes
- Sports betting legalized at state level after PASPA overturned by Supreme Court in **May 2018**
- As of 2026: **39 states + DC** have some form of legal sports betting
- States **without** legal betting: California, Texas, Idaho, Utah, Minnesota, Alabama, Georgia, South Carolina, Oklahoma, Alaska, Hawaii
- Most states require bettors to be **21+**; minimum age varies by state
- Legal US handle exceeded **$121 billion in 2023** — growing market
- Top markets by volume: New York ($19B), New Jersey ($11.9B), Illinois ($11.6B), Pennsylvania ($7.6B)
- Company must verify it operates within all applicable state regulations

---

## Sportsbooks to Know (Major US Operators)
- **DraftKings** — largest US operator, advanced ML/AI for pricing
- **FanDuel** — aggressive promotions, strong market
- **BetMGM** — MGM Resorts backing
- **Caesars** — tied to casino loyalty program
- **ESPN Bet** — Disney/ESPN partnership
- **PointsBet** — Australian operation, US presence
- **Bet365** — international powerhouse, limited US states

---

## Glossary (Quick Reference for Staff)
| Term | Definition |
|------|-----------|
| ATS | Against the Spread — whether a team covered the point spread |
| CLV | Closing Line Value — how your bet price compares to closing odds |
| Vig/Juice | Sportsbook's commission (typically ~4.5-5% on sides/totals) |
| Sharp | Professional, data-driven bettor |
| Square | Casual, public bettor |
| Steam | Rapid line movement from coordinated sharp action |
| RLM | Reverse Line Movement — line moves opposite to public betting direction |
| Handle | Total dollars wagered on a game/market |
| Hold | Sportsbook's profit margin across all bets |
| Power Rating | Team strength score used to generate spread |
| Opening Line | First odds posted |
| Closing Line | Final odds before game starts |
| F5 | First 5 Innings — MLB bet type isolating starting pitchers |
| Puck Line | NHL equivalent of point spread (+/- 1.5) |
| Run Line | MLB equivalent of point spread (+/- 1.5) |
| Push | Tie — spread lands exactly on the line, bets returned |
| Key Numbers | Most common margins of victory (NFL: 3 and 7) |
| Parlay | Multi-game bet — all legs must win |
| Teaser | Parlay with adjusted spreads (costs payout, gains points) |
| Futures | Long-term bets (e.g., Super Bowl winner) |
| Prop | Proposition bet on specific player/team stat events |
| Live Betting | Wagering during a game on updated real-time lines |

---

## Tone & Approach for Claude in This Project
- Always be educational, precise, and data-driven
- Treat staff as capable adults learning a serious business
- Reference historical data and sources where possible
- Flag legal/regulatory considerations when relevant
- When helping build the bot, prioritize clean architecture, testability, and risk management
- Never encourage reckless gambling — this is a professional operation
