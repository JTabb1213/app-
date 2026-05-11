#!/usr/bin/env python3
"""
Holder Diversity Collector
==========================
Standalone service that runs on a weekly schedule:

  1. Startup  — seed Redis from SQL (so the backend has data immediately even
                after a Redis flush/restart).
  2. On tick  — for every coin in coins.json, fetch holder data from Covalent,
                write to SQL, then write to Redis.

The backend never calls Covalent directly — it only reads from Redis (with SQL
as a cold-start fallback).

Usage:
    COVALENT_API_KEY=... DATABASE_URL=... REDIS_URL=... python main.py

Docker:
    See Dockerfile / docker-compose in this directory.
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

# Load root .env first, then local .env for overrides
def load_env_files():
    """Load .env files in order of priority (highest to lowest)."""
    root_env = Path(__file__).resolve().parents[2] / ".env"
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

load_env_files()

import config
from fetchers import covalent as covalent_fetcher
from storage import sql as sql_storage
from storage import redis_writer

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)-30s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("holder-diversity-collector")


# ── Coin list ─────────────────────────────────────────────────────────────────

def load_coins() -> list:
    """
    Load the list of coins to track from coins.json.

    Expected format:
    [
      {
        "coin_id": "chainlink",
        "chain": "ethereum",
        "contract_address": "0x514910771AF9Ca656af840dff83E8264EcF986CA"
      },
      ...
    ]
    """
    path = Path(config.COINS_FILE)
    if not path.exists():
        logger.warning(f"coins.json not found at {path}. No coins to collect.")
        return []
    with open(path) as f:
        coins = json.load(f)
    logger.info(f"Loaded {len(coins)} coins from {path}")
    return coins


# ── Core collection job ────────────────────────────────────────────────────────

def run_collection(coins: list) -> None:
    """
    Fetch, store, and cache holder data for every coin in the list.
    Errors on individual coins are logged but do not stop the rest.
    """
    logger.info(f"Starting collection run for {len(coins)} coins…")
    ok = 0
    fail = 0

    for coin in coins:
        coin_id          = coin.get("coin_id", "")
        chain            = coin.get("chain", "ethereum")
        contract_address = coin.get("contract_address", "")

        if not coin_id or not contract_address:
            logger.warning(f"Skipping malformed entry: {coin}")
            fail += 1
            continue

        snapshot = covalent_fetcher.fetch(coin_id, chain, contract_address)
        if snapshot is None:
            logger.warning(f"No data returned for {coin_id}/{chain}")
            fail += 1
            continue

        sql_ok    = sql_storage.upsert_snapshot(snapshot)
        redis_ok  = redis_writer.write_snapshot(snapshot)

        if sql_ok and redis_ok:
            ok += 1
        else:
            fail += 1

        # Be polite to the Covalent API — 5 req/s on free tier
        time.sleep(0.25)

    logger.info(f"Collection run complete — {ok} OK, {fail} failed")


# ── Cold-start Redis seed ─────────────────────────────────────────────────────

def seed_redis_from_sql() -> None:
    """
    On startup, read all existing snapshots from SQL and write them to Redis.
    This ensures the backend always has data to serve even after a Redis restart.
    """
    logger.info("Seeding Redis from SQL (cold-start)…")
    snapshots = sql_storage.get_all_snapshots()
    if not snapshots:
        logger.info("No existing snapshots in SQL — skipping seed.")
        return
    redis_writer.seed_from_snapshots(snapshots)


# ── Validation ────────────────────────────────────────────────────────────────

def _validate_config() -> bool:
    ok = True
    if not config.COVALENT_API_KEY:
        logger.error("COVALENT_API_KEY is not set.")
        ok = False
    if not config.DATABASE_URL:
        logger.error("DATABASE_URL is not set.")
        ok = False
    if not config.REDIS_URL:
        logger.error("REDIS_URL is not set.")
        ok = False
    return ok


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    logger.info("=" * 60)
    logger.info("Holder Diversity Collector starting up")
    logger.info(f"  Schedule interval : {config.SCHEDULE_INTERVAL_SECONDS}s "
                f"({config.SCHEDULE_INTERVAL_SECONDS / 86400:.1f} days)")
    logger.info(f"  Redis TTL         : {config.REDIS_TTL}s "
                f"({config.REDIS_TTL / 86400:.1f} days)")
    logger.info(f"  Fetch limit       : {config.FETCH_LIMIT} holders/token")
    logger.info("=" * 60)

    if not _validate_config():
        logger.error("Config validation failed — exiting.")
        sys.exit(1)

    coins = load_coins()
    if not coins:
        logger.error("No coins configured — nothing to collect. Add entries to coins.json.")
        sys.exit(1)

    # Seed Redis on startup so the backend can serve data immediately
    seed_redis_from_sql()

    # Run the first collection immediately, then on the configured interval
    while True:
        run_collection(coins)
        logger.info(f"Sleeping {config.SCHEDULE_INTERVAL_SECONDS}s until next run…")
        time.sleep(config.SCHEDULE_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
