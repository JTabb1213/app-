"""
Tokenomics collector — router
==============================
Dispatches to the correct source based on coin["source"].

To add a new source:
  1. Create sources/<name>.py  implementing  fetch(coin, api_key) -> dict | None
  2. Import and register it below.
"""

import logging

from .sources import coingecko
# from .sources import defillama   # future

logger = logging.getLogger(__name__)

SOURCE_MAP = {
    "coingecko": coingecko,
}


def fetch(coin: dict, api_key: str = "") -> dict | None:
    source = coin.get("source", "coingecko")
    mod    = SOURCE_MAP.get(source)
    if mod is None:
        logger.warning(f"[tokenomics] Unknown source '{source}' for {coin.get('coin_id')}")
        return None
    return mod.fetch(coin, api_key=api_key)


def fetch_batch(coin_ids: list[str], api_key: str = "") -> list[dict]:
    """Batch-fetch tokenomics for many coins via CoinGecko."""
    return coingecko.fetch_batch(coin_ids)


__all__ = ["fetch", "fetch_batch"]
