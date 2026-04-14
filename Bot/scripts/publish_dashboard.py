"""Publish dashboard to GitHub Pages.

Generates the dashboard HTML from local CSV data and pushes it
to the gh-pages branch for GitHub Pages hosting.

Works by creating a local worktree for gh-pages, writing index.html,
committing and pushing — all using the main repo's credentials.

Usage:
    python scripts/publish_dashboard.py

Called by:
    - run_bot.py (after each cycle)
    - Windows Task Scheduler (morning + post-games)
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

# Add Bot/ to path so dashboard module is importable
BOT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BOT_ROOT))

from dashboard import generate_html

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

PROJECT_ROOT = BOT_ROOT.parent
PAGES_DIR = PROJECT_ROOT / "_gh-pages"
REPO_URL = "https://github.com/FructifyMe/DaftKings.git"


def _run(cmd: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command, suppressing interactive prompts."""
    env_override = {"GIT_TERMINAL_PROMPT": "0"}
    import os
    env = {**os.environ, **env_override}
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check, env=env)


def _ensure_pages_branch() -> Path:
    """Ensure we have a local checkout of the gh-pages branch."""
    if PAGES_DIR.exists():
        # Already exists — just pull latest
        try:
            _run(["git", "pull", "origin", "gh-pages", "--ff-only"], cwd=str(PAGES_DIR), check=False)
        except Exception:
            pass
        return PAGES_DIR

    # Check if gh-pages branch exists on remote
    result = _run(
        ["git", "ls-remote", "--heads", "origin", "gh-pages"],
        cwd=str(PROJECT_ROOT), check=False,
    )

    if result.stdout.strip():
        # Branch exists — clone it
        _run([
            "git", "clone", "--branch", "gh-pages", "--single-branch",
            "--depth", "1", REPO_URL, str(PAGES_DIR),
        ])
    else:
        # Create orphan gh-pages branch
        PAGES_DIR.mkdir(parents=True)
        _run(["git", "init"], cwd=str(PAGES_DIR))
        _run(["git", "checkout", "--orphan", "gh-pages"], cwd=str(PAGES_DIR))
        _run(["git", "remote", "add", "origin", REPO_URL], cwd=str(PAGES_DIR))

    # Configure git user in this checkout
    _run(["git", "config", "user.name", "Mike"], cwd=str(PAGES_DIR))
    _run(["git", "config", "user.email", "fructifyme@gmail.com"], cwd=str(PAGES_DIR))

    return PAGES_DIR


def publish() -> bool:
    """Generate dashboard HTML and push to gh-pages branch."""
    logger.info("Generating dashboard HTML...")
    html = generate_html()
    logger.info("Generated %d chars of HTML", len(html))

    pages_dir = _ensure_pages_branch()

    # Write index.html
    (pages_dir / "index.html").write_text(html, encoding="utf-8")
    (pages_dir / ".nojekyll").touch()

    # Stage
    _run(["git", "add", "-A"], cwd=str(pages_dir))

    # Check if there are changes
    status = _run(["git", "status", "--porcelain"], cwd=str(pages_dir), check=False)
    if not status.stdout.strip():
        logger.info("No changes to dashboard — skipping push")
        return True

    # Commit
    _run(["git", "commit", "-m", "Update dashboard"], cwd=str(pages_dir))

    # Push
    push = _run(
        ["git", "push", "origin", "gh-pages", "--force"],
        cwd=str(pages_dir), check=False,
    )

    if push.returncode != 0:
        logger.error("Push failed: %s", push.stderr)
        return False

    logger.info("Dashboard published to gh-pages successfully")
    return True


if __name__ == "__main__":
    success = publish()
    sys.exit(0 if success else 1)
