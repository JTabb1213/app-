"""
News service — Redis source
Key:  crypto:news:{coin_id}
TTL:  1 hour (news refreshes frequently)
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

_PREFIX = "crypto:news:"
_TTL    = 3_600  # 1 hour


def _client():
    import redis
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return redis.from_url(url, decode_responses=True, socket_connect_timeout=2)


def get(coin_id: str) -> list | None:
    try:
        r = _client()
        raw = r.get(f"{_PREFIX}{coin_id}")
        if raw:
            return json.loads(raw)
    except Exception as exc:
        logger.warning("[news/redis] Read failed for %s: %s", coin_id, exc)
    return None


def set(coin_id: str, articles: list) -> None:
    try:
        r = _client()
        r.setex(f"{_PREFIX}{coin_id}", _TTL, json.dumps(articles))
    except Exception as exc:
        logger.warning("[news/redis] Write failed for %s: %s", coin_id, exc)
