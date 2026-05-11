"""
Tokenomics Service
==================
Serves supply & inflation data to the backend route.

Lookup order:
  1. Redis  — fast path, data written by rating/tokenomics-collector
  2. SQL    — cold-start fallback (Redis flush / first deploy)
  3. None   — return None; route will reply 404

No external API calls are made here.
"""

import json
import logging
from typing import Optional

import redis as redis_lib

from services.tokenomics import config
from services.tokenomics import database as db

logger = logging.getLogger(__name__)

_redis: redis_lib.Redis | None = None


def _get_redis() -> redis_lib.Redis:
    global _redis
    if _redis is None:
        _redis = redis_lib.from_url(config.REDIS_URL, decode_responses=True)
    return _redis


def _cache_key(coin_id: str) -> str:
    return f"{config.CACHE_KEY_PREFIX}:{coin_id.lower()}"


def get_tokenomics(coin_id: str) -> Optional[dict]:
    """
    Return the latest tokenomics snapshot for *coin_id*.

    Attaches a ``_source`` field ('cache' or 'database') so callers can see
    which layer served the data.

    Returns None when no data is available yet for this coin.
    """
    # 1. Try Redis
    try:
        r = _get_redis()
        raw = r.get(_cache_key(coin_id))
        if raw:
            data = json.loads(raw)
            data["_source"] = "cache"
            return data
    except Exception as e:
        logger.warning(f"[TokenomicsService] Redis error for {coin_id}: {e} — falling back to DB")

    # 2. Try Postgres
    data = db.get_latest_snapshot(coin_id)
    if data:
        data["_source"] = "database"
        return data

    return None
