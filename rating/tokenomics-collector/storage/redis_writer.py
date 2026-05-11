"""
Tokenomics Collector — Redis writer
=====================================
Writes supply snapshots to Redis so the backend can serve data at low latency
without touching Postgres on every request.

Key pattern:  crypto:tokenomics:{coin_id}
TTL:          config.REDIS_TTL  (default 8 days)
"""

import json
import logging

import redis as redis_lib

import config

logger = logging.getLogger(__name__)

_redis: redis_lib.Redis | None = None


def _get_redis() -> redis_lib.Redis:
    global _redis
    if _redis is None:
        _redis = redis_lib.from_url(config.REDIS_URL, decode_responses=True)
    return _redis


def _key(coin_id: str) -> str:
    return f"{config.REDIS_KEY_PREFIX}:{coin_id.lower()}"


def write_snapshot(snapshot: dict) -> bool:
    """
    Write a single tokenomics snapshot to Redis with the configured TTL.
    """
    coin_id = snapshot.get("coin_id", "")
    if not coin_id:
        logger.error("write_snapshot: snapshot missing coin_id")
        return False
    try:
        r = _get_redis()
        r.setex(_key(coin_id), config.REDIS_TTL, json.dumps(snapshot))
        logger.debug(f"[TokenomicsRedis] Wrote {_key(coin_id)} (TTL {config.REDIS_TTL}s)")
        return True
    except Exception as e:
        logger.error(f"[TokenomicsRedis] Error writing {coin_id}: {e}")
        return False


def seed_from_snapshots(snapshots: list[dict]) -> None:
    """
    Bulk-write snapshots to Redis.  Used at startup to seed from the database
    so the backend never serves stale data after a Redis flush.
    """
    if not snapshots:
        return
    try:
        r = _get_redis()
        pipe = r.pipeline()
        for snap in snapshots:
            coin_id = snap.get("coin_id", "")
            if not coin_id:
                continue
            pipe.setex(_key(coin_id), config.REDIS_TTL, json.dumps(snap))
        pipe.execute()
        logger.info(f"[TokenomicsRedis] Seeded {len(snapshots)} snapshots into Redis")
    except Exception as e:
        logger.error(f"[TokenomicsRedis] Error seeding snapshots: {e}")
