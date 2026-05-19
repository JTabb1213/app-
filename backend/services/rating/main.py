"""
Rating service — main
======================
Tries Redis first (fast path).  Falls back to SQL if the key is missing
or Redis is unavailable (e.g. cold-start before the orchestrator has run).

Usage (from a route):
    from services.rating.main import get_rating
    data = get_rating("bitcoin")   # dict | None
"""

import logging
from typing import Optional

from .sources import redis as redis_src
from .sources import sql as sql_src

logger = logging.getLogger(__name__)


def get_rating(coin_id: str) -> Optional[dict]:
    """
    Return the CCS rating snapshot for *coin_id*.

    Resolution order:
      1. Redis  (crypto:rating:{coin_id})  — O(1), preferred
      2. SQL    (rating_scores table)      — fallback if Redis miss/down

    Returns None when neither source has data for the coin.
    """
    coin_id = coin_id.lower().strip()

    # ── 1. Redis fast path ───────────────────────────────────────────────────
    data = redis_src.get(coin_id)
    if data is not None:
        logger.debug(f"[rating] Cache hit (Redis) for {coin_id}")
        data["_source"] = "redis"
        return data

    logger.info(f"[rating] Redis miss for {coin_id} — falling back to SQL")

    # ── 2. SQL fallback ──────────────────────────────────────────────────────
    data = sql_src.get(coin_id)
    if data is not None:
        logger.info(f"[rating] SQL hit for {coin_id} — populating Redis cache")
        # Write-through: cache in Redis so next request is instant
        try:
            import json
            from decimal import Decimal
            import redis as redis_lib
            _r = redis_lib.from_url(__import__('os').getenv('REDIS_URL', ''), decode_responses=True)
            _r.setex(f"crypto:rating:{coin_id}", 86_400 * 7,
                     json.dumps(data, default=lambda o: float(o) if isinstance(o, Decimal) else str(o)))
        except Exception as cache_exc:
            logger.warning(f"[rating] Redis write-through failed (non-fatal): {cache_exc}")
        data["_source"] = "sql"
        return data

    logger.warning(f"[rating] No data found for {coin_id} in Redis or SQL")
    return None
