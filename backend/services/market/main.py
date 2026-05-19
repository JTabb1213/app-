"""
Market service
==============
Resolution order:
  1. Redis  (crypto:market:{coin_id}, 24 h TTL)
  2. Postgres  (market_data table)
  3. CoinGecko live fetch → cache result in Redis + Postgres

Returns a dict or None.
"""

import logging
from datetime import datetime, timezone

from .sources import redis_source, sql, coingecko

logger = logging.getLogger(__name__)


def get_market(coin_id: str) -> dict | None:
    # 1 — Redis
    data = redis_source.get_from_redis(coin_id)
    if data:
        data["_source"] = "redis"
        logger.info("[market] %s served from Redis", coin_id)
        return data

    # 2 — Postgres
    data = sql.get(coin_id)
    if data:
        logger.info("[market] %s served from SQL", coin_id)
        # Warm Redis so the next request is faster
        redis_source.set_in_redis(coin_id, {
            "coin_id":            data["coin_id"],
            "market_cap_usd":     data["market_cap_usd"],
            "circulating_supply": data["circulating_supply"],
            "last_fetched_at":    data["last_fetched_at"],
        })
        return data

    # 3 — CoinGecko live fetch
    logger.info("[market] %s not cached, fetching from CoinGecko", coin_id)
    fresh = coingecko.fetch(coin_id)
    if not fresh:
        logger.warning("[market] CoinGecko returned nothing for %s", coin_id)
        return None

    now_iso = datetime.now(timezone.utc).isoformat()
    result = {
        "coin_id":            coin_id,
        "market_cap_usd":     fresh.get("market_cap_usd"),
        "circulating_supply": fresh.get("circulating_supply"),
        "last_fetched_at":    now_iso,
        "_source":            "coingecko",
    }

    # Persist so subsequent requests are served from cache
    redis_source.set_in_redis(coin_id, {k: v for k, v in result.items() if k != "_source"})
    if fresh.get("market_cap_usd") is not None:
        sql.upsert(coin_id, fresh["market_cap_usd"], fresh.get("circulating_supply"))

    return result
