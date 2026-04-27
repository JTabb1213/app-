#!/usr/bin/env python3
"""
Candle DB Backfill Tool
========================

Fetches historical OHLCV candles from Binance.US public REST API
(no API key required) and populates the price_candles_* tables in
your Postgres database (Supabase or any other Postgres).

Usage:
    # Backfill 1h and 1d candles for all coins in coin_aliases.json (1 year)
    python main.py

    # Specific coins only
    python main.py --coins bitcoin ethereum solana

    # Specific resolutions
    python main.py --resolutions 1h 1d

    # Custom lookback
    python main.py --days 90

    # Dry run (print what would be inserted, no DB writes)
    python main.py --dry-run

Requirements:
    pip install -r requirements.txt

Environment:
    Set DATABASE_URL in a .env file at the project root, or export it.
    Example: DATABASE_URL=postgresql://user:pass@host:5432/dbname
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
_ALIAS_PATH = os.path.join(_PROJECT_ROOT, "data", "coin_aliases.json")
_ENV_PATH = os.path.join(_PROJECT_ROOT, ".env")

load_dotenv(_ENV_PATH)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL_IPV4")

BINANCE_BASE = "https://api.binance.us/api/v3/klines"

# Binance interval string → our table name + seconds per candle
RESOLUTION_MAP = {
    "1m":  {"table": "price_candles_1m",  "seconds": 60},
    "5m":  {"table": "price_candles_5m",  "seconds": 300},
    "1h":  {"table": "price_candles_1h",  "seconds": 3600},
    "1d":  {"table": "price_candles_1d",  "seconds": 86400},
}

# Max candles Binance returns per request
BINANCE_MAX_LIMIT = 1000

# Rate limit — free Binance.US allows 1200 weight/min; each klines call = 2 weight
# 100ms sleep between requests is very conservative and safe
REQUEST_DELAY_S = 0.15


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_coin_aliases(path: str) -> dict:
    with open(path) as f:
        data = json.load(f)
    return data.get("assets", {})


def get_binance_symbol(coin_id: str, assets: dict) -> Optional[str]:
    """Return the Binance symbol for a coin id (e.g. 'bitcoin' → 'BTCUSDT')."""
    entry = assets.get(coin_id, {})
    sym = entry.get("exchange_symbols", {}).get("binance")
    if sym:
        return f"{sym}USDT"
    # Fallback: use the generic symbol field
    generic = entry.get("symbol", "")
    if generic:
        return f"{generic}USDT"
    return None


def fetch_candles(symbol: str, interval: str, start_ms: int, end_ms: int) -> list:
    """
    Fetch OHLCV candles from Binance.US for a time range.
    Paginates automatically if the range spans more than 1000 candles.
    Returns a list of dicts: {bucket, open, high, low, close, volume, tick_count}
    """
    candles = []
    current_start = start_ms

    while current_start < end_ms:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": current_start,
            "endTime": end_ms,
            "limit": BINANCE_MAX_LIMIT,
        }

        resp = requests.get(BINANCE_BASE, params=params, timeout=15)

        if resp.status_code == 400:
            # Symbol not found on Binance.US — skip silently
            return []

        resp.raise_for_status()
        rows = resp.json()

        if not rows:
            break

        for row in rows:
            # Binance klines format:
            # [open_time, open, high, low, close, volume, close_time, ...]
            open_time_ms = row[0]
            bucket_dt = datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc)

            candles.append({
                "bucket": bucket_dt,
                "open":   float(row[1]),
                "high":   float(row[2]),
                "low":    float(row[3]),
                "close":  float(row[4]),
                "volume": float(row[5]),
                "tick_count": 1,  # each Binance candle = 1 aggregated tick
            })

        # Advance past the last candle's open time
        last_open_ms = rows[-1][0]
        seconds = RESOLUTION_MAP[interval]["seconds"]
        current_start = last_open_ms + (seconds * 1000)

        if len(rows) < BINANCE_MAX_LIMIT:
            break

        time.sleep(REQUEST_DELAY_S)

    return candles


def upsert_candles(conn, table: str, coin_id: str, candles: list, is_daily: bool):
    """Upsert candles into the given table. Uses ON CONFLICT DO UPDATE."""
    if not candles:
        return 0

    # 1d table uses DATE type for bucket; others use TIMESTAMPTZ
    if is_daily:
        rows = [
            (coin_id, c["bucket"].date(), c["open"], c["high"], c["low"],
             c["close"], c["volume"], 0, c["tick_count"])
            for c in candles
        ]
    else:
        rows = [
            (coin_id, c["bucket"], c["open"], c["high"], c["low"],
             c["close"], c["volume"], 0, c["tick_count"])
            for c in candles
        ]

    sql = f"""
        INSERT INTO {table}
            (coin_id, bucket, open, high, low, close, volume, exchange_count, tick_count)
        VALUES %s
        ON CONFLICT (coin_id, bucket) DO UPDATE SET
            open           = EXCLUDED.open,
            high           = EXCLUDED.high,
            low            = EXCLUDED.low,
            close          = EXCLUDED.close,
            volume         = EXCLUDED.volume,
            tick_count     = EXCLUDED.tick_count
    """

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, rows, page_size=500)
    conn.commit()
    return len(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Backfill historical OHLCV candles from Binance.US into Postgres."
    )
    parser.add_argument(
        "--coins", nargs="+", metavar="COIN_ID",
        help="Specific coin IDs to backfill (e.g. bitcoin ethereum). "
             "Defaults to all coins in coin_aliases.json."
    )
    parser.add_argument(
        "--resolutions", nargs="+", default=["1h", "1d"],
        choices=list(RESOLUTION_MAP.keys()),
        help="Candle resolutions to fetch. Default: 1h 1d"
    )
    parser.add_argument(
        "--days", type=int, default=365,
        help="How many days back to fetch. Default: 365"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch data but don't write to DB."
    )
    args = parser.parse_args()

    # -- Load aliases --------------------------------------------------------
    if not os.path.exists(_ALIAS_PATH):
        print(f"ERROR: coin_aliases.json not found at {_ALIAS_PATH}")
        sys.exit(1)

    assets = load_coin_aliases(_ALIAS_PATH)
    coin_ids = args.coins if args.coins else sorted(assets.keys())
    print(f"Coins to backfill: {len(coin_ids)}")
    print(f"Resolutions:       {args.resolutions}")
    print(f"Lookback:          {args.days} days")
    print(f"Dry run:           {args.dry_run}")
    print()

    # -- DB connection -------------------------------------------------------
    conn = None
    if not args.dry_run:
        if not DATABASE_URL:
            print("ERROR: DATABASE_URL is not set. Add it to your .env file.")
            sys.exit(1)
        conn = psycopg2.connect(DATABASE_URL)
        print("Connected to database.\n")

    # -- Time range ----------------------------------------------------------
    now_ms = int(time.time() * 1000)
    start_ms = int((datetime.now(tz=timezone.utc) - timedelta(days=args.days)).timestamp() * 1000)

    # -- Backfill loop -------------------------------------------------------
    total_inserted = 0
    skipped = 0

    for coin_id in coin_ids:
        binance_symbol = get_binance_symbol(coin_id, assets)
        if not binance_symbol:
            print(f"  [{coin_id}] No Binance symbol — skipping")
            skipped += 1
            continue

        for resolution in args.resolutions:
            cfg = RESOLUTION_MAP[resolution]
            table = cfg["table"]
            is_daily = (resolution == "1d")

            print(f"  [{coin_id}] {resolution} ({binance_symbol}) ...", end=" ", flush=True)

            try:
                candles = fetch_candles(binance_symbol, resolution, start_ms, now_ms)
            except requests.HTTPError as e:
                print(f"HTTP error: {e}")
                continue
            except Exception as e:
                print(f"Error: {e}")
                continue

            if not candles:
                print("no data (symbol not on Binance.US)")
                continue

            if args.dry_run:
                print(f"{len(candles)} candles (dry run — not written)")
                continue

            inserted = upsert_candles(conn, table, coin_id, candles, is_daily)
            total_inserted += inserted
            print(f"{inserted} candles upserted")

            time.sleep(REQUEST_DELAY_S)

    if conn:
        conn.close()

    print()
    print(f"Done. Total rows upserted: {total_inserted}  |  Coins skipped: {skipped}")


if __name__ == "__main__":
    main()
