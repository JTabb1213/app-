"""
Covalent holder fetcher.
Fetches top token holders and computes concentration metrics.

Return shape (or None on failure):
{
    coin_id, chain, contract_address, source,
    snapshot_time,       # ISO 8601 UTC
    holder_count,        # int
    top_1_pct,           # float — % held by #1 holder
    top_10_pct,          # float — % held by top 10
    top_100_pct,         # float — % held by top 100
    gini,                # float 0-1 (higher = more concentrated)
    hhi,                 # float 0-1 (higher = more concentrated)
    top_holders: [       # top 10 addresses for display
        {rank, address, pct}
    ]
}
"""

import logging
import requests
from datetime import datetime, timezone
from typing import Optional

import config

logger = logging.getLogger(__name__)


# ── Metrics ────────────────────────────────────────────────────────────────────

def _compute_metrics(balances: list) -> dict:
    """
    Compute concentration metrics from a descending-sorted balance list.
    All inputs are raw integer token units (not human-readable).
    """
    if not balances:
        return {}
    n = len(balances)
    total = sum(balances)
    if total == 0:
        return {}

    top_1_pct   = balances[0]         / total * 100
    top_10_pct  = sum(balances[:10])  / total * 100
    top_100_pct = sum(balances[:100]) / total * 100

    # Gini coefficient (0 = perfect equality, 1 = one holder owns everything)
    gini = (2 * sum((i + 1) * b for i, b in enumerate(balances))) / (n * total) - (n + 1) / n

    # Herfindahl-Hirschman Index (0 = many small holders, 1 = monopoly)
    hhi = sum((b / total) ** 2 for b in balances)

    return {
        "holder_count": n,
        "top_1_pct":    round(top_1_pct, 2),
        "top_10_pct":   round(top_10_pct, 2),
        "top_100_pct":  round(top_100_pct, 2),
        "gini":         round(gini, 4),
        "hhi":          round(hhi, 4),
    }


# ── Fetcher ────────────────────────────────────────────────────────────────────

def fetch(coin_id: str, chain: str, contract_address: str) -> Optional[dict]:
    """
    Fetch top holders from Covalent for a single token.

    Args:
        coin_id:          Canonical coin id ("chainlink", "uniswap", …)
        chain:            Chain name key from config.COVALENT_CHAIN_IDS
        contract_address: ERC-20 contract (0x…)

    Returns:
        Normalized snapshot dict, or None on any error.
    """
    if not config.COVALENT_API_KEY:
        logger.error("[Covalent] COVALENT_API_KEY is not set.")
        return None

    chain_id = config.COVALENT_CHAIN_IDS.get(chain)
    if chain_id is None:
        logger.warning(f"[Covalent] Chain '{chain}' not in COVALENT_CHAIN_IDS — skipping {coin_id}.")
        return None

    url = f"{config.COVALENT_BASE_URL}/{chain_id}/tokens/{contract_address}/token_holders_v2/"
    params  = {"page-size": config.FETCH_LIMIT, "page-number": 0}
    headers = {"Authorization": f"Bearer {config.COVALENT_API_KEY}"}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        if data.get("error"):
            logger.error(f"[Covalent] API error for {coin_id}: {data.get('error_message')}")
            return None

        items = data.get("data", {}).get("items", [])
        if not items:
            logger.warning(f"[Covalent] No holders returned for {coin_id} on {chain}.")
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
            "source":           "covalent",
            "snapshot_time":    datetime.now(timezone.utc).isoformat(),
            "top_holders":      top_holders,
            **metrics,
        }

    except requests.HTTPError as e:
        logger.error(f"[Covalent] HTTP {e.response.status_code} for {coin_id}: {e}")
    except requests.RequestException as e:
        logger.error(f"[Covalent] Network error for {coin_id}: {e}")
    except Exception as e:
        logger.exception(f"[Covalent] Unexpected error for {coin_id}: {e}")

    return None
