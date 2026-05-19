"""
Market Data Collector
=====================
Runs on a fixed timer (default every 6 hours).
On each cycle:
  1. Load all tracked coin_ids from the rating_scores table.
  2. Fetch market data (market_cap_usd, circulating_supply, price_usd, volume_24h)
     from CoinGecko in batches.
  3. Upsert each result to:
       - PostgreSQL  →  market_data table
       - Redis       →  crypto:market:{coin_id}  (TTL = REDIS_TTL)

This means the backend API will almost always be able to serve from Redis/SQL
without hitting CoinGecko on every user request.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from decimal import Decimal

import psycopg2
import psycopg2.extras
import redis
import requests

import config

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("market-collector")

# ── DB / Redis connections ────────────────────────────────────────────────────

_pg   = None
_rdb  = None

def _get_pg():
    global _pg
    try:
        if _pg is None or _pg.closed:
            raise psycopg2.OperationalError("no conn")
        _pg.cursor().execute("SELECT 1")
    except Exception:
        _pg = psycopg2.connect(config.DATABASE_URL, connect_timeout=10)
        logger.info("[DB] Connected to PostgreSQL")
    return _pg


def _get_redis():
    global _rdb
    if _rdb is None:
        _rdb = redis.from_url(config.REDIS_URL, decode_responses=True)
        logger.info("[Redis] Connected")
    return _rdb


# ── Load tracked coins ────────────────────────────────────────────────────────

def load_coin_ids() -> list[str]:
    """Return all coin_ids currently in rating_scores."""
    try:
        conn = _get_pg()
        with conn.cursor() as cur:
            cur.execute("SELECT coin_id FROM rating_scores ORDER BY coin_id")
            rows = cur.fetchall()
        ids = [r[0] for r in rows]
        logger.info("[DB] Loaded %d tracked coins", len(ids))
        return ids
    except Exception as exc:
        logger.error("[DB] load_coin_ids failed: %s", exc)
        return []


# ── CoinGecko fetch ───────────────────────────────────────────────────────────

_BASE    = config.COINGECKO_API_BASE_URL
_TIMEOUT = 15


def fetch_batch(coin_ids: list[str]) -> dict[str, dict]:
    """
    Fetch a batch of up to BATCH_SIZE coins from /coins/markets.
    Returns {coin_id: {market_cap_usd, circulating_supply, price_usd, volume_24h}}.
    """
    headers = {"x-cg-demo-api-key": config.COINGECKO_KEY} if config.COINGECKO_KEY else {}
    ids_str = ",".join(coin_ids)
    try:
        resp = requests.get(
            f"{_BASE}/coins/markets",
            headers=headers,
            params={
                "vs_currency":           "usd",
                "ids":                   ids_str,
                "per_page":              len(coin_ids),
                "page":                  1,
                "sparkline":             "false",
                "price_change_percentage": "24h",
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        results = {}
        for item in resp.json():
            cid = item.get("id", "").lower()
            if cid:
                results[cid] = {
                    "market_cap_usd":     item.get("market_cap"),
                    "circulating_supply": item.get("circulating_supply"),
                    "price_usd":          item.get("current_price"),
                    "volume_24h":         item.get("total_volume"),
                }
        logger.info("[CoinGecko] Fetched %d/%d coins", len(results), len(coin_ids))
        return results
    except requests.exceptions.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else "?"
        if code == 429:
            logger.warning("[CoinGecko] Rate limited — sleeping 60 s")
            time.sleep(60)
        else:
            logger.warning("[CoinGecko] HTTP %s: %s", code, exc)
        return {}
    except Exception as exc:
        logger.warning("[CoinGecko] Fetch error: %s", exc)
        return {}


# ── Upsert SQL ────────────────────────────────────────────────────────────────

def upsert_sql(coin_id: str, data: dict) -> bool:
    try:
        conn = _get_pg()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO market_data (
                    coin_id, price_usd, market_cap, circulating_supply,
                    volume_24h, updated_at
                ) VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (coin_id) DO UPDATE SET
                    price_usd          = EXCLUDED.price_usd,
                    market_cap         = EXCLUDED.market_cap,
                    circulating_supply = EXCLUDED.circulating_supply,
                    volume_24h         = EXCLUDED.volume_24h,
                    updated_at         = NOW()
                """,
                (
                    coin_id,
                    data.get("price_usd"),
                    data.get("market_cap_usd"),
                    data.get("circulating_supply"),
                    data.get("volume_24h"),
                ),
            )
        conn.commit()
        return True
    except Exception as exc:
        logger.error("[DB] upsert failed for %s: %s", coin_id, exc)
        try:
            _get_pg().rollback()
        except Exception:
            pass
        return False


# ── Write Redis ───────────────────────────────────────────────────────────────

def _default(o):
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(f"Not serializable: {type(o)}")


def write_redis(coin_id: str, data: dict) -> bool:
    try:
        rdb = _get_redis()
        payload = {
            "coin_id":            coin_id,
            "market_cap_usd":     data.get("market_cap_usd"),
            "circulating_supply": data.get("circulating_supply"),
            "price_usd":          data.get("price_usd"),
            "volume_24h":         data.get("volume_24h"),
            "last_fetched_at":    datetime.now(timezone.utc).isoformat(),
        }
        rdb.setex(
            f"crypto:market:{coin_id}",
            config.REDIS_TTL,
            json.dumps(payload, default=_default),
        )
        return True
    except Exception as exc:
        logger.warning("[Redis] write failed for %s: %s", coin_id, exc)
        return False


# ── Main cycle ────────────────────────────────────────────────────────────────

def run_once():
    logger.info("═" * 55)
    logger.info("Market collector cycle starting")
    coin_ids = load_coin_ids()
    if not coin_ids:
        logger.warning("No tracked coins found — skipping cycle")
        return

    ok = fail = 0
    # Process in batches
    for batch_start in range(0, len(coin_ids), config.BATCH_SIZE):
        batch = coin_ids[batch_start: batch_start + config.BATCH_SIZE]
        results = fetch_batch(batch)

        for coin_id in batch:
            data = results.get(coin_id)
            if not data:
                logger.warning("[%s] No CoinGecko data — skipping", coin_id)
                fail += 1
                continue
            sql_ok    = upsert_sql(coin_id, data)
            redis_ok  = write_redis(coin_id, data)
            if sql_ok:
                ok += 1
                logger.debug("[%s] ✓ market data saved (redis=%s)", coin_id, redis_ok)
            else:
                fail += 1

        if batch_start + config.BATCH_SIZE < len(coin_ids):
            time.sleep(config.REQUEST_DELAY)

    logger.info("Market cycle complete — ok=%d  fail=%d", ok, fail)


def main():
    logger.info("Market Data Collector starting (interval=%ds)", config.RUN_INTERVAL)
    while True:
        try:
            run_once()
        except Exception as exc:
            logger.exception("Unhandled error in run_once: %s", exc)
        logger.info("Sleeping %d s until next cycle", config.RUN_INTERVAL)
        time.sleep(config.RUN_INTERVAL)


if __name__ == "__main__":
    main()
