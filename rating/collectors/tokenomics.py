"""
Collector: Tokenomics
======================
Pure data fetcher — no SQL, no Redis.
Returns max supply and inflation potential from CoinGecko.

Circulating supply and market cap are intentionally excluded — they are
short-term metrics not suitable for a long-term rating.

Returns dict or None on failure (per coin):
{
    coin_id, symbol, name,
    max_supply,                    # None = unlimited
    total_supply,
    inflation_potential_pct,       # % of max supply not yet issued (None if unlimited)
    snapshot_time,
    source
}
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

import requests

logger = logging.getLogger(__name__)

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
BATCH_SIZE         = 100   # CoinGecko max is 250; use 100 to be safe on free tier
BATCH_DELAY_SECS   = 7     # polite pause between batches on free tier

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
        "coin_id":                  coin_id,
        "name":                     market.get("name"),
        "symbol":                   (market.get("symbol") or "").upper(),
        "max_supply":               max_supply,
        "total_supply":             total_supply,
        "inflation_potential_pct":  inflation_potential_pct,
        "snapshot_time":            datetime.now(timezone.utc).isoformat(),
        "source":                   "CoinGecko",
    }


def fetch_batch(coin_ids: list[str]) -> list[dict]:
    """
    Fetch tokenomics snapshots for all provided coin IDs.
    Batches requests to respect CoinGecko rate limits.
    """
    snapshots: list[dict] = []

    for i in range(0, len(coin_ids), BATCH_SIZE):
        batch   = coin_ids[i : i + BATCH_SIZE]
        batch_n = i // BATCH_SIZE + 1
        logger.info(f"CoinGecko batch {batch_n} — fetching {len(batch)} coins")
        markets = _markets_request(batch)
        for market in markets:
            snap = _build_snapshot(market)
            if snap:
                snapshots.append(snap)
        if i + BATCH_SIZE < len(coin_ids):
            time.sleep(BATCH_DELAY_SECS)

    logger.info(f"CoinGecko: fetched {len(snapshots)} tokenomics snapshots")
    return snapshots
