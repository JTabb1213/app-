"""
Collector: Holder Diversity
============================
Pure data fetcher — no SQL, no Redis.
Returns holder concentration metrics from Covalent for a single token.

Returns dict or None on failure:
{
    coin_id, chain, contract_address, source, snapshot_time,
    holder_count,
    top_1_pct,    # % held by #1 holder
    top_10_pct,   # % held by top 10 holders
    top_100_pct,  # % held by top 100 holders
    gini,         # 0-1 (higher = more concentrated)
    hhi,          # 0-1 (higher = more concentrated)
    top_holders:  [ {rank, address, pct} ]
}
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import requests

logger = logging.getLogger(__name__)

COVALENT_BASE_URL = "https://api.covalenthq.com/v1"
COVALENT_CHAIN_IDS = {
    "ethereum":  "eth-mainnet",
    "polygon":   "matic-mainnet",
    "bsc":       "bsc-mainnet",
    "avalanche": "avalanche-mainnet",
    "arbitrum":  "arbitrum-mainnet",
    "optimism":  "optimism-mainnet",
    "solana":    "solana-mainnet",
}
FETCH_LIMIT = 200  # top N holders to fetch


def _compute_metrics(balances: list) -> dict:
    if not balances:
        return {}
    n     = len(balances)
    total = sum(balances)
    if total == 0:
        return {}

    top_1_pct   = balances[0]         / total * 100
    top_10_pct  = sum(balances[:10])  / total * 100
    top_100_pct = sum(balances[:100]) / total * 100
    gini = (2 * sum((i + 1) * b for i, b in enumerate(balances))) / (n * total) - (n + 1) / n
    hhi  = sum((b / total) ** 2 for b in balances)

    return {
        "holder_count": n,
        "top_1_pct":    round(top_1_pct, 2),
        "top_10_pct":   round(top_10_pct, 2),
        "top_100_pct":  round(top_100_pct, 2),
        "gini":         round(gini, 4),
        "hhi":          round(hhi, 4),
    }


def fetch(coin: dict, api_key: str) -> Optional[dict]:
    """
    Fetch top token holders from Covalent for a single coin.

    Args:
        coin:    dict with coin_id, chain, contract_address keys
        api_key: Covalent API key
    """
    if not api_key:
        logger.error("[Covalent] COVALENT_API_KEY is not set")
        return None

    coin_id          = coin["coin_id"]
    chain            = coin.get("chain", "")
    contract_address = coin.get("contract_address", "")

    chain_id = COVALENT_CHAIN_IDS.get(chain)
    if not chain_id:
        logger.warning(f"[Covalent] Chain '{chain}' not supported — skipping {coin_id}")
        return None

    url     = f"{COVALENT_BASE_URL}/{chain_id}/tokens/{contract_address}/token_holders_v2/"
    params  = {"page-size": FETCH_LIMIT, "page-number": 0}
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        if data.get("error"):
            logger.error(f"[Covalent] API error for {coin_id}: {data.get('error_message')}")
            return None

        items = data.get("data", {}).get("items", [])
        if not items:
            logger.warning(f"[Covalent] No holders for {coin_id} on {chain}")
            return None

        balances = sorted(
            [int(h.get("balance", 0)) for h in items if h.get("balance")],
            reverse=True,
        )
        metrics = _compute_metrics(balances)
        if not metrics:
            return None

        total = sum(balances)
        top_holders = [
            {
                "rank":    i + 1,
                "address": items[i].get("address", ""),
                "pct":     round(balances[i] / total * 100, 4) if total > 0 else 0,
            }
            for i in range(min(10, len(items)))
        ]

        return {
            "coin_id":          coin_id,
            "chain":            chain,
            "contract_address": contract_address,
            "source":           "Covalent",
            "snapshot_time":    datetime.now(timezone.utc).isoformat(),
            **metrics,
            "top_holders":      top_holders,
        }
    except Exception as exc:
        logger.error(f"[Covalent] fetch error for {coin_id}: {exc}")
        return None
