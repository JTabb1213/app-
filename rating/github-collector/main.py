#!/usr/bin/env python3
"""
GitHub Activity Collector
=========================
Standalone service that runs on a weekly schedule:

  1. Startup  — seed Redis from SQL so the backend has data immediately
                even after a Redis flush / restart.
  2. On tick  — for every coin in coins.json:
       a. Read the previous total_commit_count from SQL (for delta)
       b. Fetch current GitHub metrics (commits, contributors, stars, etc.)
       c. Compute delta_commits = current_total - previous_total
          → this is "commits in the last 7 days" without any API date filtering
       d. Write enriched snapshot (with delta_commits) to SQL then Redis

Commit delta logic:
  - First run ever: delta = total_commit_count (no previous baseline)
  - Subsequent runs: delta = current_total - previous_total

Usage:
    GITHUB_TOKEN=ghp_... DATABASE_URL=... REDIS_URL=... python main.py

Docker:
    See Dockerfile in this directory.
"""

import json
import logging
import os
import sys
import time
from pathlib import Path


# ── Env loading ────────────────────────────────────────────────────────────────
def _load_env_files():
    root_env  = Path(__file__).resolve().parents[2] / ".env"
    local_env = Path(__file__).resolve().parent / ".env"
    for env_file in [root_env, local_env]:
        if not env_file.exists():
            continue
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip()
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value

_load_env_files()

import config
from fetchers import github as github_fetcher
from storage import sql as sql_storage
from storage import redis_writer

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)-30s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("github-collector")


# ── Coin list ──────────────────────────────────────────────────────────────────

def load_coins() -> list:
    """
    Load coins from coins.json.

    Expected format:
    [
      { "coin_id": "bitcoin", "symbol": "BTC", "owner": "bitcoin", "repo": "bitcoin" },
      { "coin_id": "pepe", "symbol": "PEPE", "owner": "", "repo": "" }
    ]
    """
    path = Path(config.COINS_FILE)
    if not path.exists():
        logger.error(f"Coins file not found: {path}")
        sys.exit(1)
    with open(path) as f:
        coins = json.load(f)
    valid = [c for c in coins if c.get("coin_id")]
    logger.info(f"Loaded {len(valid)} coins from {path.name}")
    return valid


# ── Single-coin run ────────────────────────────────────────────────────────────

def process_coin(coin: dict) -> bool:
    """
    Fetch, enrich with delta, store to SQL and Redis.
    Returns True on success, False on failure.
    """
    coin_id = coin["coin_id"]

    # Skip coins with no GitHub repo configured
    if not coin.get("owner") or not coin.get("repo"):
        logger.info(f"[{coin_id}] No repo configured — skipping")
        return True

    # Fetch current GitHub data
    snapshot = github_fetcher.fetch_snapshot(coin)
    if not snapshot:
        logger.warning(f"[{coin_id}] Fetch returned nothing — skipping")
        return False

    # Compute commit delta vs previous run
    previous = sql_storage.get_previous_snapshot(coin_id)
    if previous:
        prev_total = previous.get("total_commit_count", 0)
        curr_total = snapshot.get("total_commit_count", 0)
        snapshot["delta_commits"] = max(curr_total - prev_total, 0)
        logger.info(
            f"[{coin_id}] commits: {prev_total} → {curr_total} "
            f"(+{snapshot['delta_commits']} this period)"
        )
    else:
        # First run — no baseline yet; treat total as the delta
        snapshot["delta_commits"] = snapshot.get("total_commit_count", 0)
        logger.info(f"[{coin_id}] First run — delta_commits = total ({snapshot['delta_commits']})")

    # Write to SQL (persists the new total for next run's delta calc)
    sql_ok = sql_storage.upsert_snapshot(snapshot)
    if not sql_ok:
        logger.error(f"[{coin_id}] SQL write failed")
        return False

    # Write to Redis (what the backend actually reads)
    redis_ok = redis_writer.write_snapshot(snapshot)
    if not redis_ok:
        logger.warning(f"[{coin_id}] Redis write failed — data still in SQL")

    return True


# ── Main loop ──────────────────────────────────────────────────────────────────

def run_once():
    """Fetch and store GitHub data for all coins."""
    coins = load_coins()

    logger.info(f"Starting GitHub data collection for {len(coins)} coins")
    ok, fail, skip = 0, 0, 0

    for coin in coins:
        if not coin.get("owner") or not coin.get("repo"):
            skip += 1
            continue
        success = process_coin(coin)
        if success:
            ok += 1
        else:
            fail += 1

    logger.info(
        f"Collection complete — success: {ok}, failed: {fail}, skipped (no repo): {skip}"
    )


def main():
    if not config.DATABASE_URL:
        logger.error("DATABASE_URL is not set. Exiting.")
        sys.exit(1)
    if not config.REDIS_URL:
        logger.error("REDIS_URL is not set. Exiting.")
        sys.exit(1)

    # ── Cold-start: seed Redis from SQL ───────────────────────────────────────
    logger.info("Seeding Redis from SQL …")
    existing = sql_storage.load_all_snapshots()
    redis_writer.seed_from_snapshots(existing)
    logger.info(f"Seeded {len(existing)} snapshots from SQL into Redis")

    # ── Scheduled loop ─────────────────────────────────────────────────────────
    interval = config.SCHEDULE_INTERVAL_SECONDS
    logger.info(f"Schedule: every {interval // 3600}h ({interval}s)")

    while True:
        run_once()
        logger.info(f"Sleeping {interval}s until next run …")
        time.sleep(interval)


if __name__ == "__main__":
    main()
