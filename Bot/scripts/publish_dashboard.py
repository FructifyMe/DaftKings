"""Publish dashboard to GitHub Pages.

Generates the dashboard HTML from local CSV data and pushes it
to the gh-pages branch for GitHub Pages hosting.

Usage:
    python scripts/publish_dashboard.py

Called by:
    - run_bot.py (after each cycle)
    - Windows Task Scheduler (morning + post-games)
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Add Bot/ to path so dashboard module is importable
BOT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BOT_ROOT))

from dashboard import generate_html

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

PROJECT_ROOT = BOT_ROOT.parent
REPO_URL_FALLBACK = "https://github.com/FructifyMe/DaftKings.git"


def get_repo_url() -> str:
    """Get the remote origin URL from the main repo."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(PROJECT_ROOT),
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return REPO_URL_FALLBACK


def publish() -> bool:
    """Generate dashboard HTML and push to gh-pages branch."""
    logger.info("Generating dashboard HTML...")
    html = generate_html()
    logger.info("Generated %d chars of HTML", len(html))

    repo_url = get_repo_url()
    logger.info("Repo URL: %s", repo_url)

    # Work in a temp directory to avoid messing with the main repo
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Try to clone the gh-pages branch; if it doesn't exist, create it
        clone_result = subprocess.run(
            ["git", "clone", "--branch", "gh-pages", "--single-branch",
             "--depth", "1", repo_url, str(tmp / "pages")],
            capture_output=True, text=True,
        )

        if clone_result.returncode != 0:
            # Branch doesn't exist yet — create orphan
            logger.info("gh-pages branch not found, creating...")
            pages_dir = tmp / "pages"
            pages_dir.mkdir()
            subprocess.run(["git", "init"], cwd=str(pages_dir), check=True,
                           capture_output=True)
            subprocess.run(["git", "checkout", "--orphan", "gh-pages"],
                           cwd=str(pages_dir), check=True, capture_output=True)
            subprocess.run(["git", "remote", "add", "origin", repo_url],
                           cwd=str(pages_dir), check=True, capture_output=True)
        else:
            pages_dir = tmp / "pages"

        # Write the dashboard HTML as index.html
        index_path = pages_dir / "index.html"
        index_path.write_text(html, encoding="utf-8")

        # Also write a .nojekyll file so GitHub serves raw HTML
        (pages_dir / ".nojekyll").touch()

        # Stage, commit, push
        subprocess.run(["git", "add", "-A"], cwd=str(pages_dir), check=True,
                       capture_output=True)

        # Check if there are changes
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(pages_dir), capture_output=True, text=True,
        )
        if not status.stdout.strip():
            logger.info("No changes to dashboard — skipping push")
            return True

        subprocess.run(
            ["git", "commit", "-m", "Update dashboard"],
            cwd=str(pages_dir), check=True, capture_output=True,
        )

        push_result = subprocess.run(
            ["git", "push", "origin", "gh-pages", "--force"],
            cwd=str(pages_dir), capture_output=True, text=True,
        )

        if push_result.returncode != 0:
            logger.error("Push failed: %s", push_result.stderr)
            return False

        logger.info("Dashboard published to gh-pages successfully")
        return True


if __name__ == "__main__":
    success = publish()
    sys.exit(0 if success else 1)
