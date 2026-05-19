"""
Volume service
==============
Returns buy/sell volume for a coin over a given time window.

Resolution order:
  1. Redis  (vol:{coin_id} hash written by volume-aggregator)
  (No SQL fallback — volume data is ephemeral by design.)

Returns a dict or None.
"""

import logging

from .sources import redis_source
from .sources.redis_source import WINDOWS

logger = logging.getLogger(__name__)


def get_volume(coin_id: str, window: str) -> dict | None:
    """
    Fetch aggregated buy/sell volume for *coin_id* over *window*.

    Args:
        coin_id: Canonical coin ID (e.g. "bitcoin").
        window:  Time window string. Must be one of: 5m, 30m, 1h, 4h, 6h, 24h.

    Returns:
        Dict with buy_volume, sell_volume, total_volume, buy_pct, sell_pct,
        bucket_count, and _source — or None if window is invalid or Redis is down.
    """
    if window not in WINDOWS:
        logger.warning(f"[volume] Unsupported window '{window}'")
        return None

    data = redis_source.get_volume(coin_id, window)
    if data is None:
        logger.warning(f"[volume] Redis unavailable for {coin_id}/{window}")
    return data
