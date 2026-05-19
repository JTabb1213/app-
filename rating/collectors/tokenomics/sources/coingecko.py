"""
Tokenomics — CoinGecko source
==============================
Fetches max supply, total supply, and inflation potential from the
CoinGecko /coins/markets endpoint (free tier compatible).

Returned dict matches the shape defined in base.py.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

import requests

logger = logging.getLogger(__name__)

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
BATCH_SIZE         = 100
BATCH_DELAY_SECS   = 7

_SESSION = requests.Session()
_SESSION.headers.update({"Accept": "application/json"})


def _markets_request(coin_ids: list[str]) -> list[dict]:
    url    = f"{COINGECKO_BASE_URL}/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids":         ",".join(coin_ids),
        "order":       "market_cap_desc",
        "per_page":    len(coin_ids),
        "page":        1,
        "sparkline":   "false",
    }
    try:
        resp = _SESSION.get(url, params=params, timeout=20)
        if resp.status_code == 429:
            logger.warning("CoinGecko rate limit — sleeping 60s")
            time.sleep(60)
            resp = _SESSION.get(url, params=params, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        logger.error(f"CoinGecko /coins/markets error: {exc}")
        return []


def _build_snapshot(market: dict) -> Optional[dict]:
    coin_id = market.get("id")
    if not coin_id:
        return None
    max_supply   = market.get("max_supply")
    total_supply = market.get("total_supply") or market.get("circulating_supply")
    inflation_potential_pct = None
    if max_supply and max_supply > 0 and total_supply is not None:
        remaining = max_supply - total_supply
        inflation_potential_pct = round((remaining / max_supply) * 100, 4)
    return {
        "coin_id":                 coin_id,
        "name":                    market.get("name"),
        "symbol":                  (market.get("symbol") or "").upper(),
        "max_supply":              max_supply,
        "total_supply":            total_supply,
        "inflation_potential_pct": inflation_potential_pct,
        "snapshot_time":           datetime.now(timezone.utc).isoformat(),
        "source":                  "coingecko",
    }


def fetch(coin: dict, api_key: str = "") -> Optional[dict]:
    """Fetch tokenomics for a single coin."""
    coin_id = coin["coin_id"]
    markets = _markets_request([coin_id])
    if not markets:
        return None
    return _build_snapshot(markets[0])


def fetch_batch(coin_ids: list[str]) -> list[dict]:
    """Batch-fetch tokenomics for many coins (respects CoinGecko rate limits)."""
    snapshots: list[dict] = []
    for i in range(0, len(coin_ids), BATCH_SIZE):
        batch = coin_ids[i: i + BATCH_SIZE]
        logger.info(f"CoinGecko batch {i // BATCH_SIZE + 1} — {len(batch)} coins")
        for market in _markets_request(batch):
            snap = _build_snapshot(market)
            if snap:
                snapshots.append(snap)
        if i + BATCH_SIZE < len(coin_ids):
            time.sleep(BATCH_DELAY_SECS)
    logger.info(f"CoinGecko: {len(snapshots)} snapshots fetched")
    return snapshots
