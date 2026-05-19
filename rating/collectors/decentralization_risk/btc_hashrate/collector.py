"""
Bitcoin Hashrate / Miner Concentration — mempool.space collector
=================================================================
Fetches mining pool hashrate distribution from mempool.space (free, no key).
Computes Nakamoto coefficient and pool concentration metrics.

Used for: Bitcoin (BTC) only.
Why: For PoW coins, consensus power = hashrate. Pool concentration is the
     correct decentralization signal, not wallet richlist.

Config keys used: none (mempool.space is public).
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import requests

logger  = logging.getLogger(__name__)
BASE    = "https://mempool.space/api/v1"
TIMEOUT = 15


def _fetch_pools(days: int = 7) -> list | None:
    """Fetch mining pool block distribution from mempool.space."""
    try:
        resp = requests.get(f"{BASE}/mining/pools/{days}d", timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("pools", [])
    except Exception as exc:
        logger.warning(f"[BTCHashrate] pools/{days}d failed: {exc}")
        return None


def _compute_metrics(pools: list) -> dict:
    weights = sorted(
        [float(p.get("blockCount", 0)) for p in pools if p.get("blockCount", 0) > 0],
        reverse=True,
    )
    if not weights:
        return {}

    asc   = sorted(weights)
    total = sum(weights)
    n     = len(weights)

    top_1   = weights[0]        / total * 100
    top_10  = sum(weights[:10]) / total * 100 if n >= 10 else sum(weights) / total * 100
    gini    = (2 * sum((i + 1) * b for i, b in enumerate(asc))) / (n * total) - (n + 1) / n
    hhi     = sum((b / total) ** 2 for b in weights)

    # Nakamoto coefficient: min pools to reach >51% hashrate
    cumulative, nakamoto = 0, 0
    for w in weights:
        cumulative += w
        nakamoto   += 1
        if cumulative / total > 0.51:
            break

    return {
        "pool_count":           n,
        "top_1_pct":            round(top_1, 2),
        "top_10_pct":           round(top_10, 2),
        "top_100_pct":          None,   # not meaningful for pool count
        "gini":                 round(gini, 4),
        "hhi":                  round(hhi, 4),
        "nakamoto_coefficient": nakamoto,
    }


def fetch(coin: dict, config: dict) -> Optional[dict]:
    """
    Fetch BTC miner concentration.

    Args:
        coin:   Must contain "coin_id" (should be "bitcoin").
        config: Unused — mempool.space requires no key.

    Returns:
        Standardised decentralization result dict, or None on failure.
    """
    coin_id = coin.get("coin_id", "bitcoin")

    # Try 7-day window first, fall back to 1-day
    pools = _fetch_pools(days=7) or _fetch_pools(days=1)
    if not pools:
        logger.error(f"[BTCHashrate] Could not fetch pool data for {coin_id}")
        return None

    metrics = _compute_metrics(pools)
    if not metrics:
        return None

    pools_sorted = sorted(pools, key=lambda p: p.get("blockCount", 0), reverse=True)
    total_blocks = sum(p.get("blockCount", 0) for p in pools)

    return {
        "coin_id":          coin_id,
        "source":           "mempool.space",
        "snapshot_time":    datetime.now(timezone.utc).isoformat(),
        **metrics,
        # richlist fields not applicable
        "holder_count":    None,
        "insider_pct":     None,
        "circulating_ratio": None,
        "top_holders": [
            {
                "rank":       i + 1,
                "address":    p.get("name") or p.get("slug") or "Unknown",
                "pct":        round(p.get("blockCount", 0) / total_blocks * 100, 2) if total_blocks else 0,
            }
            for i, p in enumerate(pools_sorted[:10])
        ],
    }
