"""
Writers: Redis
===============
Writes the final computed score to Redis so the backend can serve it
at low latency without hitting Postgres on every request.

Key pattern:  crypto:rating:{coin_id}
TTL:          Passed in at call time (should match the orchestrator's schedule)
"""

import json
import logging
from decimal import Decimal

import redis as redis_lib

logger = logging.getLogger(__name__)

KEY_PREFIX = "crypto:rating"

_redis: redis_lib.Redis | None = None


def init(redis_url: str):
    """Open (or re-open) the Redis connection."""
    global _redis
    _redis = redis_lib.from_url(redis_url, decode_responses=True)
    logger.info("[Redis] Connected")


def _get_redis() -> redis_lib.Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialised — call writers.redis_writer.init() first")
    return _redis


def _key(coin_id: str) -> str:
    return f"{KEY_PREFIX}:{coin_id.lower()}"


def _dumps(obj) -> str:
    return json.dumps(obj, default=lambda o: float(o) if isinstance(o, Decimal) else str(o))


def write_score(score_row: dict, ttl_seconds: int) -> bool:
    """
    Write a final score snapshot to Redis with the given TTL.

    Args:
        score_row:   Full score dict (same as what goes to SQL)
        ttl_seconds: Key TTL in seconds (should equal the schedule interval + buffer)
    """
    coin_id = score_row.get("coin_id", "")
    if not coin_id:
        logger.error("[Redis] write_score: missing coin_id")
        return False
    try:
        r = _get_redis()
        r.setex(_key(coin_id), ttl_seconds, _dumps(score_row))
        logger.debug(f"[Redis] Wrote {_key(coin_id)} TTL={ttl_seconds}s")
        return True
    except Exception as exc:
        logger.error(f"[Redis] write_score({coin_id}): {exc}")
        return False


def seed_from_sql(rows: list[dict], ttl_seconds: int) -> None:
    """
    Bulk-write existing SQL rows into Redis at startup (cold-start seed).
    """
    if not rows:
        return
    try:
        r    = _get_redis()
        pipe = r.pipeline()
        for row in rows:
            coin_id = row.get("coin_id", "")
            if coin_id:
                pipe.setex(_key(coin_id), ttl_seconds, _dumps(row))
        pipe.execute()
        logger.info(f"[Redis] Cold-start seeded {len(rows)} rating keys")
    except Exception as exc:
        logger.error(f"[Redis] seed_from_sql error: {exc}")
