"""
Candle Writer — builds and persists hourly OHLCV candles to Postgres.

How it works
============
Every price tick that flows through the RedisWriter is also passed here
via ``update(coin_id, price, timestamp)``.

For each coin, we keep an in-memory ``_Window`` — the running open/high/low/
close for the current hour.  When a tick arrives whose hour bucket is
*different* from the window's bucket, the window has just closed.  We then:

  1. Look up the matching hour's traded volume from Redis (``vol:<coin_id>``
     hash — written by the volume-aggregator, keys are minute timestamps).
  2. Insert the completed candle into ``price_candles_1h`` in Postgres via an
     ``ON CONFLICT DO UPDATE`` upsert so re-runs are idempotent.
  3. Start a fresh window for the new hour.

Volume lookup
=============
The ``vol:<coin_id>`` Redis hash contains one entry per minute bucket
(Unix timestamp rounded down to the nearest minute).  To get the volume
for a completed hour we sum all minute buckets whose timestamp falls within
[hour_start, hour_start + 3600).

Crash safety
============
In-memory windows are lost on crash.  This means at most ONE incomplete hour
of OHLC data could be missed.  The candle-aggregator will still be able to
roll up whatever complete hourly candles exist, and the backfill tool can
be used to patch any gaps.

Usage
=====
Instantiate once in main.py, call ``update()`` on every normalized tick,
and call ``connect()`` after the Redis client is available.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

import psycopg2
import psycopg2.extras
import redis.asyncio as aioredis

import config

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _hour_bucket(ts: float) -> int:
    """Round a Unix timestamp down to the start of its hour."""
    return int(ts // 3600) * 3600


# ── In-memory window ───────────────────────────────────────────────────────────

@dataclass
class _Window:
    """Tracks OHLC for a single coin over one hour bucket."""
    coin_id:    str
    bucket:     int          # Unix timestamp of hour start
    open:       float
    high:       float
    low:        float
    close:      float
    tick_count: int = 0

    def update(self, price: float) -> None:
        self.high  = max(self.high,  price)
        self.low   = min(self.low,   price)
        self.close = price
        self.tick_count += 1

    @classmethod
    def new(cls, coin_id: str, bucket: int, price: float) -> "_Window":
        return cls(
            coin_id=coin_id,
            bucket=bucket,
            open=price,
            high=price,
            low=price,
            close=price,
            tick_count=1,
        )


# ── Main class ─────────────────────────────────────────────────────────────────

class CandleWriter:
    """
    Receives price ticks, accumulates hourly OHLCV windows, and flushes
    completed candles to Postgres.

    Thread / async safety: all methods are called from the same asyncio
    event loop as RedisWriter, so no locking is needed.
    """

    def __init__(self) -> None:
        self._windows:    Dict[str, _Window]   = {}
        self._redis:      Optional[aioredis.Redis] = None
        self._pg_conn:    Optional[psycopg2.extensions.connection] = None
        self._write_count: int = 0

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    async def connect(self, redis_client: aioredis.Redis) -> None:
        """Store the shared Redis client and open the Postgres connection."""
        self._redis = redis_client
        self._pg_conn = self._pg_connect()
        logger.info("[CandleWriter] Ready")

    def _pg_connect(self) -> psycopg2.extensions.connection:
        """Connect to Postgres, trying IPv4 fallback if primary fails."""
        db_url = config.DATABASE_URL
        if not db_url:
            raise ValueError("DATABASE_URL is not set — CandleWriter cannot persist candles.")
        try:
            conn = psycopg2.connect(db_url)
            logger.info("[CandleWriter] Connected to Postgres (primary URL)")
            return conn
        except psycopg2.OperationalError as e:
            fallback = config.DATABASE_URL_IPV4
            if fallback:
                logger.warning(
                    f"[CandleWriter] Primary DB connection failed ({e}), "
                    "trying IPv4 fallback…"
                )
                conn = psycopg2.connect(fallback)
                logger.info("[CandleWriter] Connected to Postgres (IPv4 fallback)")
                return conn
            raise

    def _ensure_pg(self) -> psycopg2.extensions.connection:
        """Return a live Postgres connection, reconnecting if needed."""
        try:
            if self._pg_conn is None or self._pg_conn.closed:
                raise psycopg2.OperationalError("no connection")
            self._pg_conn.cursor().execute("SELECT 1")
        except Exception:
            self._pg_conn = self._pg_connect()
        return self._pg_conn

    # ── Price tick ingestion ───────────────────────────────────────────────────

    def update(self, coin_id: str, price: float, timestamp: float) -> None:
        """
        Called for every normalized price tick.
        If the tick's hour differs from the current window, the window is
        closed and flushed asynchronously.
        """
        if price <= 0:
            return

        bucket = _hour_bucket(timestamp)

        if coin_id not in self._windows:
            # First tick for this coin — open a new window
            self._windows[coin_id] = _Window.new(coin_id, bucket, price)
            return

        window = self._windows[coin_id]

        if bucket == window.bucket:
            # Same hour — just update OHLC
            window.update(price)
        else:
            # Hour boundary crossed — close this window and open a new one
            # Schedule the async flush without blocking the hot path
            asyncio.ensure_future(self._close_window(window))
            self._windows[coin_id] = _Window.new(coin_id, bucket, price)

    # ── Window close & persist ─────────────────────────────────────────────────

    async def _close_window(self, window: _Window) -> None:
        """Fetch volume from Redis and upsert the completed candle to Postgres."""
        try:
            volume = await self._get_hour_volume(window.coin_id, window.bucket)
            await asyncio.get_event_loop().run_in_executor(
                None, self._upsert_candle, window, volume
            )
        except Exception as e:
            logger.error(
                f"[CandleWriter] Failed to close window "
                f"{window.coin_id}@{window.bucket}: {e}"
            )

    async def _get_hour_volume(self, coin_id: str, hour_bucket: int) -> float:
        """
        Sum all per-minute volume buckets that fall within the closed hour.

        The volume-aggregator stores vol:<coin_id> as a Redis hash where
        each field is a minute-timestamp string and the value is a JSON
        object with ``buy`` and ``sell`` keys.
        """
        if self._redis is None:
            return 0.0

        key = f"vol:{coin_id}"
        try:
            raw = await self._redis.hgetall(key)
        except Exception as e:
            logger.warning(f"[CandleWriter] Redis volume lookup failed for {coin_id}: {e}")
            return 0.0

        total = 0.0
        hour_end = hour_bucket + 3600

        for ts_str, val_json in raw.items():
            try:
                minute_ts = int(ts_str)
                if hour_bucket <= minute_ts < hour_end:
                    data = json.loads(val_json)
                    total += float(data.get("buy",  0))
                    total += float(data.get("sell", 0))
            except (ValueError, KeyError, json.JSONDecodeError):
                continue

        return round(total, 8)

    def _upsert_candle(self, window: _Window, volume: float) -> None:
        """Write a completed 1h candle to Postgres (called in thread executor)."""
        sql = """
            INSERT INTO price_candles_1h
                (coin_id, bucket, open, high, low, close, volume, tick_count)
            VALUES
                (%s,
                 to_timestamp(%s) AT TIME ZONE 'UTC',
                 %s, %s, %s, %s, %s, %s)
            ON CONFLICT (coin_id, bucket)
            DO UPDATE SET
                open       = EXCLUDED.open,
                high       = EXCLUDED.high,
                low        = EXCLUDED.low,
                close      = EXCLUDED.close,
                volume     = EXCLUDED.volume,
                tick_count = EXCLUDED.tick_count
        """
        params = (
            window.coin_id,
            window.bucket,
            window.open,
            window.high,
            window.low,
            window.close,
            volume,
            window.tick_count,
        )

        try:
            conn = self._ensure_pg()
            with conn.cursor() as cur:
                cur.execute(sql, params)
            conn.commit()
            self._write_count += 1
            logger.info(
                f"[CandleWriter] ✓ {window.coin_id} "
                f"bucket={window.bucket} "
                f"O={window.open} H={window.high} L={window.low} C={window.close} "
                f"vol={volume} ticks={window.tick_count}"
            )
        except Exception as e:
            logger.error(f"[CandleWriter] Postgres upsert failed: {e}")
            try:
                self._pg_conn.rollback()
            except Exception:
                self._pg_conn = None

    # ── Stats ──────────────────────────────────────────────────────────────────

    @property
    def stats(self) -> dict:
        return {
            "open_windows":  len(self._windows),
            "candles_written": self._write_count,
        }
