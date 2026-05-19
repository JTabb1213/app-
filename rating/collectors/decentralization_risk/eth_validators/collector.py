"""
Ethereum Validator Concentration — rated.network collector
===========================================================
Fetches staking entity concentration from rated.network.
Computes Nakamoto coefficient and entity concentration metrics.

Used for: Ethereum (ETH) only.
Why: For PoS coins, consensus power = stake. Named entity concentration
     (Lido, Coinbase, etc.) is far more meaningful than wallet richlist.

Config keys used:
    config["RATED_API_KEY"]   (optional but recommended — increases rate limits)
    Free key at: https://bit.ly/ratedAPIkeys
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import requests

logger  = logging.getLogger(__name__)
BASE    = "https://api.rated.network/v0"
TIMEOUT = 15


def _get_headers(api_key: str) -> dict:
    h = {"Accept": "application/json", "User-Agent": "CryptoRating/1.0"}
    if api_key:
        h["Authorization"] = f"Bearer {api_key}"
    return h


def _fetch_operators(api_key: str, size: int = 30) -> list | None:
    """Fetch top staking operators (entities) from rated.network."""
    url = f"{BASE}/eth/operators?size={size}&sortOrder=desc&sortKey=avgValidatorEffectiveness"
    try:
        resp = requests.get(url, headers=_get_headers(api_key), timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", data) if isinstance(data, dict) else data
    except Exception as exc:
        logger.warning(f"[ETHValidators] operators fetch failed: {exc}")
        return None


def _fetch_network_overview(api_key: str) -> dict | None:
    """Fetch total validator count for denominator calculations."""
    try:
        resp = requests.get(f"{BASE}/eth/network/overview",
                            headers=_get_headers(api_key), timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def _compute_metrics(operators: list, total_validators: int | None) -> dict:
    weights = []
    for e in operators:
        w = (e.get("validatorCount") or e.get("activeStake") or
             e.get("totalStake") or e.get("stake") or 0)
        weights.append(float(w))

    weights = [w for w in weights if w > 0]
    if not weights:
        return {}

    desc  = sorted(weights, reverse=True)
    asc   = sorted(weights)
    total = sum(desc)
    n     = len(desc)

    top_1   = desc[0]        / total * 100
    top_3   = sum(desc[:3])  / total * 100
    top_10  = sum(desc[:10]) / total * 100 if n >= 10 else sum(desc) / total * 100
    gini    = (2 * sum((i + 1) * b for i, b in enumerate(asc))) / (n * total) - (n + 1) / n
    hhi     = sum((b / total) ** 2 for b in desc)

    # Nakamoto: min entities to control >33% of stake (ETH attack threshold)
    cumulative, nakamoto = 0, 0
    for w in desc:
        cumulative += w
        nakamoto   += 1
        if cumulative / total > 0.33:
            break

    return {
        "entity_count":         n,
        "top_1_pct":            round(top_1, 2),
        "top_3_pct":            round(top_3, 2),
        "top_10_pct":           round(top_10, 2),
        "top_100_pct":          None,
        "gini":                 round(gini, 4),
        "hhi":                  round(hhi, 4),
        "nakamoto_coefficient": nakamoto,
    }


def fetch(coin: dict, config: dict) -> Optional[dict]:
    """
    Fetch ETH validator/staking entity concentration.

    Args:
        coin:   Must contain "coin_id" (should be "ethereum").
        config: May contain "RATED_API_KEY".

    Returns:
        Standardised decentralization result dict, or None on failure.
    """
    coin_id = coin.get("coin_id", "ethereum")
    api_key = config.get("RATED_API_KEY", "")

    operators = _fetch_operators(api_key, size=30)
    if not operators:
        logger.error(f"[ETHValidators] Could not fetch operator data for {coin_id}")
        return None

    overview          = _fetch_network_overview(api_key)
    total_validators  = overview.get("validatorCount") if overview else None

    metrics = _compute_metrics(operators, total_validators)
    if not metrics:
        return None

    ops_sorted   = sorted(operators, key=lambda e: float(
        e.get("validatorCount") or e.get("activeStake") or 0), reverse=True)

    return {
        "coin_id":       coin_id,
        "source":        "rated.network",
        "snapshot_time": datetime.now(timezone.utc).isoformat(),
        **metrics,
        # richlist / vesting fields not applicable
        "holder_count":     None,
        "insider_pct":      None,
        "circulating_ratio": None,
        "top_holders": [
            {
                "rank":    i + 1,
                "address": (e.get("displayName") or e.get("name") or
                            e.get("operatorTag") or e.get("id", "Unknown")),
                "pct":     round(float(e.get("validatorCount") or e.get("activeStake") or 0)
                                 / sum(float(x.get("validatorCount") or x.get("activeStake") or 0)
                                       for x in operators) * 100, 2),
            }
            for i, e in enumerate(ops_sorted[:10])
        ],
    }
