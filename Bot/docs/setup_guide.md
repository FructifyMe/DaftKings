# DaftKings Bot Setup Guide

## 1. Prerequisites

- Python 3.11+ (tested on 3.11-3.14)
- pip (comes with Python)
- Git (optional, for version control)
- Windows 10/11 (local dev) or Ubuntu 22.04 (VPS)

## 2. Clone and Install

```bash
cd C:\Users\YourName\Documents
git clone <your-repo-url> DaftKings
cd DaftKings/Bot

pip install -r requirements.txt
```

Verify install:
```bash
python -c "from config import CONFIG; print('Config OK:', CONFIG.paper_mode)"
```

## 3. Environment Setup (.env)

Copy the template and fill in your keys:

```bash
cp .env.example .env
```

### Where to get each key:

**ANTHROPIC_API_KEY**
1. Go to https://console.anthropic.com
2. Create an API key under Settings > API Keys
3. Paste into `.env`

**ODDS_API_KEY**
1. Go to https://the-odds-api.com
2. Sign up for free tier (500 requests/month)
3. Copy your API key from the dashboard

**KALSHI_API_KEY / KALSHI_API_SECRET**
1. Create account at https://kalshi.com
2. Go to Settings > API Keys
3. Generate a new key pair
4. For paper trading, no deposit needed (sandbox environment)

**TELEGRAM_BOT_TOKEN** (see Section 4 below)

**TELEGRAM_CHAT_ID** (see Section 4 below)

## 4. Telegram Bot Setup (Step by Step)

### Create the bot:
1. Open Telegram, search for `@BotFather`
2. Send `/newbot`
3. Choose a name (e.g., "DaftKings Bot")
4. Choose a username (e.g., "daftkings_alerts_bot")
5. BotFather gives you a token like `123456:ABCdefGHI...`
6. Paste this into `TELEGRAM_BOT_TOKEN` in `.env`

### Get your chat ID:
1. Search for `@userinfobot` on Telegram
2. Send it any message
3. It replies with your user ID (a number like `123456789`)
4. Paste this into `TELEGRAM_CHAT_ID` in `.env`

### Test it:
```bash
python -c "
from src.alerting.telegram_bot import TelegramBot
tb = TelegramBot()
tb._send('DaftKings Bot connected!')
"
```
You should receive the message in Telegram.

## 5. Windows Task Scheduler Setup (Local Dev)

1. Open Task Scheduler (search "Task Scheduler" in Start)
2. Click "Create Basic Task"
3. Name: `DaftKings Bot`
4. Trigger: Daily, repeat every 10 minutes for 24 hours
5. Action: Start a program
   - Program: `C:\Python311\python.exe` (your Python path)
   - Arguments: `C:\path\to\DaftKings\Bot\scripts\run_bot.py`
   - Start in: `C:\path\to\DaftKings\Bot`
6. Check "Run whether user is logged on or not"
7. Finish

To find your Python path:
```bash
where python
```

## 6. Hostinger VPS Setup (Ubuntu)

SSH into your VPS:

```bash
ssh user@your-vps-ip
```

Install Python and dependencies:
```bash
sudo apt update && sudo apt install python3 python3-pip -y
cd /home/daftkings/Bot
pip3 install -r requirements.txt
cp .env.example .env
nano .env  # fill in your keys
```

Set up cron:
```bash
crontab -e
```

Add these lines:
```cron
*/10 * * * * /usr/bin/python3 /home/daftkings/Bot/scripts/run_bot.py >> /home/daftkings/Bot/data/logs/cron.log 2>&1
```

Verify cron is running:
```bash
crontab -l
tail -f /home/daftkings/Bot/data/logs/cron.log
```

## 7. Verify the Bot Is Working

After the first scheduled run (or manual run):

```bash
python scripts/run_bot.py
```

Check for:
- Telegram receives a message (if odds are found)
- `data/logs/bot.log` has entries
- `data/logs/run_log.csv` exists with a row
- No errors in stdout

Check logs:
```bash
# Last 20 lines of bot log
tail -20 data/logs/bot.log

# Today's runs
cat data/logs/run_log.csv
```

## 8. Reading bets_log.csv

The bets log has one row per decision (bet or pass). Key columns:

| Column | What it means |
|--------|--------------|
| `recommended_side` | home/away/over/under |
| `estimated_edge` | How much edge Haiku estimated (0.05 = 5%) |
| `confidence` | Haiku's confidence (0.70+ needed for bet) |
| `actual_stake_usd` | Dollar amount bet (0 = pass) |
| `paper_mode` | True = simulated, False = real money |
| `haiku_reasoning` | Full text explanation from Claude |
| `result` | W/L/Push (filled after game completes) |
| `pnl_usd` | Profit/loss from this bet |

Open in Excel or pandas:
```python
import pandas as pd
df = pd.read_csv("data/logs/bets_log.csv")
print(df[df["actual_stake_usd"] > 0])  # Show only placed bets
```

## 9. Switching from Paper to Live

**DO NOT do this until:**
- At least 1 week of paper trading is complete
- You have reviewed the bets_log.csv and are satisfied
- Mike has explicitly approved

To switch:
1. Edit `.env`
2. Change `PAPER_MODE=true` to `PAPER_MODE=false`
3. Ensure your Kalshi account has funds
4. Restart the scheduler

The bot will now place real orders on Kalshi.

## 10. Kill Switch Reset

The kill switch activates when daily drawdown exceeds 40%. It logs to `data/logs/kill_switch.log`.

**It auto-resets at midnight** (new day = new daily stats).

To manually check status:
```python
from src.risk_manager.kill_switch import KillSwitch
ks = KillSwitch()
print(ks.get_daily_stats())
print("Active:", ks.is_active())
```

To force-reset (if needed):
1. Open `data/logs/kill_switch.log`
2. Delete or rename the file
3. The next cycle will run normally
