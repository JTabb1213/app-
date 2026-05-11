"""
Redis writer for holder diversity snapshots.
Sets keys with a weekly TTL so the backend can read them without
knowing anything about Covalent or the SQL table.

Key format:  crypto:holder_diversity:{chain}:{coin_id}
Value:       JSON-serialized snapshot dict
TTL:         config.REDIS_TTL (default 8 days)
"""

import json
import logging
import redis
from typing import Optional

import config

logger = logging.getLogger(__name__)

_client: Optional[redis.Redis] = None


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(config.REDIS_URL, decode_responses=True)
        _client.ping()
        logger.info("[Redis] Connected")
    return _client


def _key(coin_id: str, chain: str) -> str:
    return f"{config.REDIS_KEY_PREFIX}:{chain.lower()}:{coin_id.lower()}"


def write_snapshot(snapshot: dict) -> bool:
    """
    Serialize and store a snapshot in Redis with the configured TTL.
    Returns True on success.
    """
    try:
        client = _get_client()
        k = _key(snapshot["coin_id"], snapshot["chain"])
        client.setex(k, config.REDIS_TTL, json.dumps(snapshot))
        logger.info(f"[Redis] Wrote {k} (TTL {config.REDIS_TTL}s)")
        return True
    except Exception as e:
        logger.error(f"[Redis] Write failed for {snapshot.get('coin_id')}: {e}")
        return False


def seed_from_snapshots(snapshots: list) -> int:
    """
    Bulk-write a list of snapshots to Redis.
    Called on startup to warm the cache from SQL.
    Returns the number of keys successfully written.
    """
    written = 0
    for snap in snapshots:
        if write_snapshot(snap):
            written += 1
    logger.info(f"[Redis] Cold-start seed complete — {written}/{len(snapshots)} keys written")
    return written
