"""
Volume Redis source
===================
Reads per-minute buy/sell buckets written by the volume-aggregator.

Redis key schema (written by volume-aggregator):
  vol:{coin_id}  — HASH
    field = minute_ts (str unix timestamp of the minute bucket)
    value = JSON {"b": float, "s": float}  (buy / sell notional USD)
"""

import json
import logging
import os
import time

import redis

logger = logging.getLogger(__name__)

# Window label → seconds
WINDOWS: dict[str, int] = {
    "5m":  5 * 60,
    "30m": 30 * 60,
    "1h":  60 * 60,
    "4h":  4 * 60 * 60,
    "6h":  6 * 60 * 60,
    "24h": 24 * 60 * 60,
}

_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        url = os.getenv("REDIS_URL", "redis://redis:6379")
        _client = redis.from_url(url, decode_responses=True, socket_connect_timeout=5)
    return _client


def get_volume(coin_id: str, window: str) -> dict | None:
    """
    Return aggregated buy/sell volume for *coin_id* over *window*.

    Returns None on Redis error.
    Returns a dict with zeroed values if the key exists but has no
    buckets in the requested window (e.g. service just started).
    """
    window_seconds = WINDOWS.get(window)
    if window_seconds is None:
        return None  # caller validates window before calling

    try:
        r = _get_client()
        raw = r.hgetall(f"vol:{coin_id}")
    except Exception as exc:
        logger.error(f"[volume/redis] Redis error for {coin_id}: {exc}")
        return None

    cutoff = int(time.time()) - window_seconds
    buy_total = 0.0
    sell_total = 0.0
    bucket_count = 0
    all_exchanges: set[str] = set()

    for minute_ts_str, value_str in (raw or {}).items():
        try:
            if int(minute_ts_str) < cutoff:
                continue
            bucket = json.loads(value_str)
            buy_total  += float(bucket.get("b", 0))
            sell_total += float(bucket.get("s", 0))
            # "ex" is stored as a list of exchange names by the volume-aggregator
            ex = bucket.get("ex", [])
            if isinstance(ex, list):
                all_exchanges.update(ex)
            bucket_count += 1
        except (ValueError, json.JSONDecodeError):
            continue

    total = buy_total + sell_total
    buy_pct = round(buy_total / total * 100, 1) if total > 0 else 50.0

    return {
        "coin_id":           coin_id,
        "window":            window,
        "buy_volume_coins":  round(buy_total, 6),
        "sell_volume_coins": round(sell_total, 6),
        "total_volume_coins":round(total, 6),
        "buy_pct":           buy_pct,
        "sell_pct":          round(100 - buy_pct, 1),
        "bucket_count":      bucket_count,
        "exchange_count":    len(all_exchanges),
        "exchanges":         sorted(all_exchanges),
        "_source":           "redis",
    }
