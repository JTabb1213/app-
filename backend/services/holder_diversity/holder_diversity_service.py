"""
Holder Diversity Service
Read-only. Data is populated by rating/holder-diversity-collector.
Read priority: Redis -> SQL -> None
"""

import json
import logging
from typing import Optional

from services.holder_diversity import config
from services.holder_diversity import database as hd_db

logger = logging.getLogger(__name__)

_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None:
        import redis
        _redis_client = redis.from_url(config.REDIS_URL, decode_responses=True)
    return _redis_client


def _cache_key(coin_id: str, chain: str) -> str:
    return f"{config.CACHE_KEY_PREFIX}:{chain.lower()}:{coin_id.lower()}"


def get_holder_diversity(
    coin_id: str,
    chain: str = "ethereum",
) -> Optional[dict]:
    """Return the latest holder snapshot. Redis first, SQL fallback."""
    # 1. Redis
    try:
        raw = _get_redis().get(_cache_key(coin_id, chain))
        if raw:
            data = json.loads(raw)
            data["_source"] = "cache"
            return data
    except Exception as e:
        logger.warning(f"[HolderDiversityService] Redis read failed, falling back to SQL: {e}")

    # 2. SQL fallback
    row = hd_db.get_latest_snapshot(coin_id, chain)
    if row:
        row["_source"] = "database"
        return row

    return None
