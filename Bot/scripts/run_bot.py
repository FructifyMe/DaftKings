#!/usr/bin/env python3
"""Entry point for Windows Task Scheduler / cron.

Usage:
    python scripts/run_bot.py          # Full scan + analyze + settle cycle
    python scripts/run_bot.py --settle # Settlement only (grade completed bets)

Called every 10 minutes by the scheduler. Runs one full bot cycle and exits.
"""
import sys
import os
from pathlib import Path

# Ensure Bot/ is on the Python path regardless of working directory
bot_root = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, bot_root)
os.chdir(bot_root)

import logging

# Set up logging before importing anything else
log_dir = Path(bot_root) / "data" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "bot.log"),
        logging.StreamHandler(),
    ],
)

from main import run_cycle, run_settlement

if __name__ == "__main__":
    if "--settle" in sys.argv:
        run_settlement()
    else:
        run_cycle()
