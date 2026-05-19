"""
Candles service — main
=======================
Thin orchestration layer between the route and the SQL source.
Candle data is read-only from Postgres; there is no Redis cache for candles
(they are time-series and too large to cache per-coin).

Usage:
    from services.candles.main import get_candles, VALID_RESOLUTIONS
    result = get_candles("bitcoin", "1h", 200)
    # result is either:
    #   None       — invalid resolution
    #   []         — valid resolution, no data yet
    #   [{ time, open, high, low, close, volume }, ...]
"""

import logging
from typing import Optional

from .sources.sql import get, VALID_RESOLUTIONS

logger = logging.getLogger(__name__)


def get_candles(coin_id: str, resolution: str, limit: int) -> Optional[list[dict]]:
    """
    Fetch OHLCV candles for *coin_id*.

    Args:
        coin_id:    CoinGecko canonical id (e.g. "bitcoin")
        resolution: one of VALID_RESOLUTIONS keys ("1m","5m","1h","1d","1w","1month")
        limit:      max number of candles to return (capped at 1000)

    Returns:
        None  — resolution is not valid
        []    — resolution is valid but no data exists yet
        list  — candles in chronological order (oldest first)
    """
    coin_id    = coin_id.lower().strip()
    limit      = min(max(1, limit), 1000)
    return get(coin_id, resolution, limit)


__all__ = ["get_candles", "VALID_RESOLUTIONS"]
