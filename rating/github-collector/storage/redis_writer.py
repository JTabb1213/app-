"""
GitHub Collector — Redis writer
=================================
Key pattern:  crypto:github:{coin_id}
TTL:          config.REDIS_TTL  (default 8 days)

The snapshot stored in Redis includes delta_commits (commits since last run),
which is what the score orchestrator will use for the Community & Dev score.
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
    """Write a single GitHub snapshot to Redis with the configured TTL."""
    coin_id = snapshot.get("coin_id", "")
    if not coin_id:
        logger.error("write_snapshot: missing coin_id")
        return False
    try:
        r = _get_redis()
        r.setex(_key(coin_id), config.REDIS_TTL, json.dumps(snapshot))
        logger.debug(f"[GitHubRedis] Wrote {_key(coin_id)} (TTL {config.REDIS_TTL}s)")
        return True
    except Exception as exc:
        logger.error(f"[GitHubRedis] Error writing {coin_id}: {exc}")
        return False


def seed_from_snapshots(snapshots: list[dict]) -> None:
    """Bulk-write snapshots to Redis at startup (cold-start seed)."""
    if not snapshots:
        return
    try:
        r = _get_redis()
        pipe = r.pipeline()
        for snap in snapshots:
            coin_id = snap.get("coin_id", "")
            if coin_id:
                pipe.setex(_key(coin_id), config.REDIS_TTL, json.dumps(snap))
        pipe.execute()
        logger.info(f"[GitHubRedis] Seeded {len(snapshots)} keys from SQL")
    except Exception as exc:
        logger.error(f"[GitHubRedis] seed_from_snapshots error: {exc}")
