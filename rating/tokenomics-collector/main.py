#!/usr/bin/env python3
"""
Tokenomics Collector
====================
Standalone service that runs on a weekly schedule:

  1. Startup  — seed Redis from SQL so the backend has data immediately even
                after a Redis flush / restart.
  2. On tick  — fetch circulating/total/max supply and price data for every
                coin in coins.json from CoinGecko, write to SQL, then Redis.

The backend never calls CoinGecko directly — it reads from Redis (with SQL
as a cold-start fallback).

Usage:
    DATABASE_URL=... REDIS_URL=... python main.py

Docker:
    See Dockerfile / docker-compose in this directory.
"""

import json
import logging
import os
import sys
import time
from pathlib import Path


# ── Env loading ───────────────────────────────────────────────────────────────
def load_env_files():
    """Load .env files in order: root .env (shared), then local .env (overrides)."""
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


load_env_files()

import config
from fetchers import coingecko as coingecko_fetcher
from storage import sql as sql_storage
from storage import redis_writer

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)-30s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("tokenomics-collector")


# ── Coin list ─────────────────────────────────────────────────────────────────

def load_coins() -> list[str]:
    """
    Load the list of coin IDs from coins.json.

    Expected format:
    [
      { "coin_id": "bitcoin" },
      { "coin_id": "ethereum" },
      ...
    ]
    """
    path = Path(config.COINS_FILE)
    if not path.exists():
        logger.warning(f"coins.json not found at {path}.")
        return []
    with open(path) as f:
        entries = json.load(f)
    coin_ids = [e["coin_id"] for e in entries if e.get("coin_id")]
    logger.info(f"Loaded {len(coin_ids)} coins from {path}")
    return coin_ids


# ── Core collection job ────────────────────────────────────────────────────────

def run_collection(coin_ids: list[str]) -> None:
    """
    Fetch supply data from CoinGecko for all coins, then persist to SQL + Redis.
    """
    logger.info(f"Starting tokenomics collection run for {len(coin_ids)} coins…")

    snapshots = coingecko_fetcher.fetch_batch(coin_ids)

    ok = 0
    fail = 0
    for snap in snapshots:
        sql_ok   = sql_storage.upsert_snapshot(snap)
        redis_ok = redis_writer.write_snapshot(snap)
        if sql_ok and redis_ok:
            ok += 1
        else:
            fail += 1

    # Flag coins that CoinGecko returned no data for
    returned_ids = {s["coin_id"] for s in snapshots}
    for cid in coin_ids:
        if cid not in returned_ids:
            logger.warning(f"No data returned from CoinGecko for coin_id='{cid}'")
            fail += 1

    logger.info(f"Collection run complete — {ok} OK, {fail} failed/missing")


# ── Cold-start Redis seed ─────────────────────────────────────────────────────

def seed_redis_from_sql() -> None:
    """
    On startup, read all tokenomics snapshots from SQL and write them to Redis.
    This ensures the backend can serve data immediately after a Redis restart.
    """
    logger.info("Seeding Redis from SQL (cold-start)…")
    snapshots = sql_storage.get_all_snapshots()
    if not snapshots:
        logger.info("No existing tokenomics snapshots in SQL — skipping seed.")
        return
    redis_writer.seed_from_snapshots(snapshots)


# ── Validation ────────────────────────────────────────────────────────────────

def _validate_config() -> bool:
    ok = True
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
    logger.info("Tokenomics Collector starting up")
    logger.info(f"  Schedule interval : {config.SCHEDULE_INTERVAL_SECONDS}s "
                f"({config.SCHEDULE_INTERVAL_SECONDS / 86400:.1f} days)")
    logger.info(f"  Redis TTL         : {config.REDIS_TTL}s "
                f"({config.REDIS_TTL / 86400:.1f} days)")
    logger.info(f"  Batch size        : {config.BATCH_SIZE} coins/request")
    logger.info("=" * 60)

    if not _validate_config():
        logger.error("Config validation failed — exiting.")
        sys.exit(1)

    coin_ids = load_coins()
    if not coin_ids:
        logger.error("No coins configured — add entries to coins.json.")
        sys.exit(1)

    # Seed Redis on startup
    seed_redis_from_sql()

    # Run immediately, then on the configured interval
    while True:
        run_collection(coin_ids)
        logger.info(f"Sleeping {config.SCHEDULE_INTERVAL_SECONDS}s until next run…")
        time.sleep(config.SCHEDULE_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
