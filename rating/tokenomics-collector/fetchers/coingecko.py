"""
CoinGecko supply fetcher
========================
Fetches circulating supply, total supply, max supply, and price data for a
batch of coins using the /coins/markets endpoint.

No API key required (free public tier).  We batch up to BATCH_SIZE coins per
request to stay within rate limits (10–30 req/min on the free tier).
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

import requests

import config

logger = logging.getLogger(__name__)

_SESSION = requests.Session()
_SESSION.headers.update({"Accept": "application/json"})


def _coingecko_markets(coin_ids: list[str]) -> list[dict]:
    """
    Call /coins/markets for a list of coin_ids.
    Returns the raw list of market objects, or [] on failure.
    """
    url = f"{config.COINGECKO_BASE_URL}/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": ",".join(coin_ids),
        "order": "market_cap_desc",
        "per_page": len(coin_ids),
        "page": 1,
        "sparkline": "false",
    }
    try:
        resp = _SESSION.get(url, params=params, timeout=20)
        if resp.status_code == 429:
            logger.warning("CoinGecko rate limit hit — sleeping 60s")
            time.sleep(60)
            resp = _SESSION.get(url, params=params, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        logger.error(f"CoinGecko /coins/markets error: {exc}")
        return []


def _build_snapshot(market: dict) -> Optional[dict]:
    """
    Convert a single CoinGecko market object to the normalised snapshot dict
    that sql.py / redis_writer.py expect.
    """
    coin_id = market.get("id")
    if not coin_id:
        return None

    circulating = market.get("circulating_supply")
    max_supply  = market.get("max_supply")
    total       = market.get("total_supply") or circulating

    # What percentage of the max supply has NOT yet been issued?
    if max_supply and max_supply > 0 and circulating is not None:
        remaining = max_supply - circulating
        inflation_potential_pct = round((remaining / max_supply) * 100, 4)
    else:
        inflation_potential_pct = None

    return {
        "coin_id":                     coin_id,
        "name":                        market.get("name"),
        "symbol":                      (market.get("symbol") or "").upper(),
        "circulating_supply":          circulating,
        "total_supply":                total,
        "max_supply":                  max_supply,
        "price_usd":                   market.get("current_price"),
        "market_cap_usd":              market.get("market_cap"),
        "supply_inflation_potential_pct": inflation_potential_pct,
        "snapshot_time":               datetime.now(timezone.utc).isoformat(),
        "source":                      "CoinGecko",
    }


def fetch_batch(coin_ids: list[str]) -> list[dict]:
    """
    Fetch supply snapshots for a list of coin_ids.

    Splits the list into chunks of config.BATCH_SIZE to respect the CoinGecko
    URL length limit.  Returns a flat list of snapshot dicts.

    Coins with no data returned by CoinGecko are silently skipped.
    """
    snapshots: list[dict] = []

    for i in range(0, len(coin_ids), config.BATCH_SIZE):
        batch = coin_ids[i : i + config.BATCH_SIZE]
        logger.info(f"Fetching CoinGecko supply data for {len(batch)} coins "
                    f"(batch {i // config.BATCH_SIZE + 1})")
        markets = _coingecko_markets(batch)

        for market in markets:
            snap = _build_snapshot(market)
            if snap:
                snapshots.append(snap)

        # Polite pause between batches (free tier ~10 req/min)
        if i + config.BATCH_SIZE < len(coin_ids):
            time.sleep(7)

    logger.info(f"Fetched {len(snapshots)} snapshots from CoinGecko")
    return snapshots
