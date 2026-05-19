"""
Market service — CoinGecko source
===================================
Fetches market_cap_usd and circulating_supply for one coin.
Uses /coins/markets endpoint (no API key required for basic rate).
"""

import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

_BASE = "https://api.coingecko.com/api/v3"
_TIMEOUT = 10


def fetch(coin_id: str) -> dict | None:
    """
    Returns {"market_cap_usd": float, "circulating_supply": float}
    or None on failure.
    """
    api_key = os.getenv("COINGECKO_API_KEY", "")
    headers = {"x-cg-demo-api-key": api_key} if api_key else {}

    try:
        resp = requests.get(
            f"{_BASE}/coins/markets",
            headers=headers,
            params={
                "vs_currency": "usd",
                "ids": coin_id,
                "per_page": 1,
                "page": 1,
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            logger.warning("[market/coingecko] No data returned for %s", coin_id)
            return None

        item = data[0]
        return {
            "market_cap_usd":     item.get("market_cap"),
            "circulating_supply": item.get("circulating_supply"),
        }

    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 429:
            logger.warning("[market/coingecko] Rate limited for %s", coin_id)
        else:
            logger.warning("[market/coingecko] HTTP error for %s: %s", coin_id, exc)
    except Exception as exc:
        logger.warning("[market/coingecko] Fetch failed for %s: %s", coin_id, exc)

    return None
