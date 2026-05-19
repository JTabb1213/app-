"""
Read market data from Redis.
Key: crypto:market:{coin_id}
Written by an external collector or by the service itself after a CoinGecko fetch.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

REDIS_KEY_PREFIX = "crypto:market:"
MARKET_TTL = 86_400  # 24 hours


def _client():
    import redis

    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return redis.from_url(url, decode_responses=True, socket_connect_timeout=2)


def get_from_redis(coin_id: str) -> dict | None:
    try:
        r = _client()
        raw = r.get(f"{REDIS_KEY_PREFIX}{coin_id}")
        if raw:
            return json.loads(raw)
    except Exception as exc:
        logger.warning("Redis market read failed for %s: %s", coin_id, exc)
    return None


def set_in_redis(coin_id: str, data: dict) -> None:
    try:
        r = _client()
        r.setex(f"{REDIS_KEY_PREFIX}{coin_id}", MARKET_TTL, json.dumps(data))
    except Exception as exc:
        logger.warning("Redis market write failed for %s: %s", coin_id, exc)
