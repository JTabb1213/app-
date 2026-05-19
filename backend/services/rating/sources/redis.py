"""
Rating service — Redis source
==============================
Reads the pre-computed CCS score from Redis.

Key pattern:  crypto:rating:{coin_id}
Written by:   rating/writers/redis_writer.py  (score-orchestrator layer)
"""

import json
import logging
import os
from typing import Optional

import redis as redis_lib

logger     = logging.getLogger(__name__)
_client: redis_lib.Redis | None = None
KEY_PREFIX = "crypto:rating"


def _get_client() -> redis_lib.Redis:
    global _client
    if _client is None:
        url = os.getenv("REDIS_URL")
        if not url:
            raise RuntimeError("REDIS_URL not set")
        _client = redis_lib.from_url(url, decode_responses=True)
    return _client


def get(coin_id: str) -> Optional[dict]:
    """
    Fetch the rating snapshot for *coin_id* from Redis.
    Returns None if the key is missing or Redis is unreachable.
    """
    key = f"{KEY_PREFIX}:{coin_id.lower()}"
    try:
        raw = _get_client().get(key)
        if raw is None:
            logger.debug(f"[rating/redis] Cache miss: {key}")
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.warning(f"[rating/redis] Error reading {key}: {exc}")
        return None
