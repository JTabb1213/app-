#!/usr/bin/env python3
"""
Candle Aggregator Service
=========================

Builds higher-resolution candle tables by rolling up lower-resolution ones:

  price_candles_1h  →  price_candles_1d
  price_candles_1d  →  price_candles_1w
  price_candles_1w  →  price_candles_1month

Schedule:
  - Every hour  : roll 1h → 1d  (captures today's in-progress daily candle)
  - Every hour  : roll 1d → 1w  (captures this week's in-progress weekly candle)
  - Every hour  : roll 1w → 1m  (captures this month's in-progress monthly candle)

All writes are idempotent (ON CONFLICT DO UPDATE) so re-runs are safe.
If this service crashes and restarts, it simply re-aggregates — no data loss.

Usage (standalone):
    DATABASE_URL=... python main.py

Usage (Docker):
    See Dockerfile / docker-compose.local.yml
"""

import logging
import os
import sys
import time

import schedule
from dotenv import load_dotenv

import config
from aggregator import CandleAggregator

# ── Load env ──────────────────────────────────────────────────────────────────
load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s │ %(levelname)-7s │ %(name)-20s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("candle-aggregator")


# ── Scheduled job ─────────────────────────────────────────────────────────────
def run_all_aggregations(agg: CandleAggregator) -> None:
    """
    Run every roll-up in sequence.
    Called on schedule and also immediately at startup.
    """
    logger.info("─── Starting aggregation run ────────────────────────────")

    # Order matters: 1h→1d must complete before 1d→1w, etc.
    agg.aggregate(
        source_table="price_candles_1h",
        dest_table="price_candles_1d",
        dest_resolution="1d",
        source_window_hours=None,       # use all available data
    )
    agg.aggregate(
        source_table="price_candles_1d",
        dest_table="price_candles_1w",
        dest_resolution="1w",
        source_window_hours=None,
    )
    agg.aggregate(
        source_table="price_candles_1w",
        dest_table="price_candles_1month",
        dest_resolution="1month",
        source_window_hours=None,
    )

    logger.info("─── Aggregation run complete ─────────────────────────────")


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    db_url = config.DATABASE_URL
    if not db_url:
        logger.error("DATABASE_URL is not set — cannot connect to Postgres.")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("  Candle Aggregator")
    logger.info("  Rolls up 1h → 1d → 1w → 1month")
    logger.info(f"  Schedule: every {config.RUN_INTERVAL_MINUTES} minutes")
    logger.info("=" * 60)

    agg = CandleAggregator(db_url)

    # ── Run immediately on startup so gaps are filled right away ──
    run_all_aggregations(agg)

    # ── Then run on schedule ──
    schedule.every(config.RUN_INTERVAL_MINUTES).minutes.do(run_all_aggregations, agg)

    logger.info(f"Scheduler running — next run in {config.RUN_INTERVAL_MINUTES} min")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)
