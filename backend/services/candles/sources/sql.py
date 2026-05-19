"""
Candles service — PostgreSQL source
=====================================
Fetches OHLCV candlestick rows from the price_candles_* TimescaleDB tables.
Returns data in chronological order (oldest → newest) ready for charting.

Returned list item shape:
{
    time:   int   (Unix timestamp),
    open:   float,
    high:   float,
    low:    float,
    close:  float,
    volume: float,
}
"""

import logging
import os
from typing import Optional

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

VALID_RESOLUTIONS = {
    "1m":     "price_candles_1m",
    "5m":     "price_candles_5m",
    "1h":     "price_candles_1h",
    "1d":     "price_candles_1d",
    "1w":     "price_candles_1w",
    "1month": "price_candles_1month",
}

_conn = None


def _pg_connect():
    primary  = os.getenv("DATABASE_URL")
    fallback = os.getenv("DATABASE_URL_IPV4")
    try:
        conn = psycopg2.connect(primary, connect_timeout=5)
        logger.info("[CandlesDB] Connected (primary)")
        return conn
    except psycopg2.OperationalError as exc:
        if fallback and fallback != primary:
            logger.warning(f"[CandlesDB] Primary unreachable ({exc}), trying IPv4 fallback")
            conn = psycopg2.connect(fallback, connect_timeout=5)
            logger.info("[CandlesDB] Connected (IPv4 fallback)")
            return conn
        raise


def _get_conn():
    global _conn
    try:
        if _conn is None or _conn.closed:
            raise psycopg2.OperationalError("no connection")
        _conn.cursor().execute("SELECT 1")
    except Exception:
        _conn = _pg_connect()
    return _conn


def get(coin_id: str, resolution: str, limit: int) -> Optional[list[dict]]:
    """
    Fetch up to *limit* candles for *coin_id* at *resolution*.

    Returns None if *resolution* is invalid.
    Returns an empty list if no rows exist yet.
    Returns the list in chronological order (oldest first).
    """
    table = VALID_RESOLUTIONS.get(resolution)
    if table is None:
        return None

    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT bucket, open, high, low, close, volume
                FROM {table}
                WHERE coin_id = %s
                ORDER BY bucket DESC
                LIMIT %s
                """,
                (coin_id, limit),
            )
            rows = cur.fetchall()
    except Exception as exc:
        logger.error(f"[CandlesDB] Error for {coin_id}/{resolution}: {exc}")
        global _conn
        try:
            if _conn:
                _conn.close()
        except Exception:
            pass
        _conn = None
        return []

    # Reverse so result is oldest → newest (what chart libraries expect)
    candles = []
    for row in reversed(rows):
        bucket = row["bucket"]
        ts = (
            int(bucket.timestamp())
            if hasattr(bucket, "timestamp")
            else int(__import__("datetime").datetime.combine(
                bucket, __import__("datetime").time()
            ).timestamp())
        )
        candles.append({
            "time":   ts,
            "open":   float(row["open"]),
            "high":   float(row["high"]),
            "low":    float(row["low"]),
            "close":  float(row["close"]),
            "volume": float(row["volume"]),
        })
    return candles
