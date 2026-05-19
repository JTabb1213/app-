"""
Decentralization Risk — Base Dispatcher
=========================================
Single entry point for the score orchestrator.

Call:
    from rating.collectors.decentralization_risk.base import fetch

    result = fetch(coin, config)

The dispatcher reads `coin["diversity_method"]` and routes to the correct
sub-collector. All sub-collectors return the same output shape (or None).

Coin dict shape (from coins table / coin config):
    {
        "coin_id":          "bitcoin",
        "symbol":           "BTC",
        "diversity_method": "hashrate" | "validator" | "vesting" | "token_holders",
        # token_holders only:
        "chain":            "ethereum",
        "contract_address": "0x514910..."
    }

Output shape (all methods):
    {
        "coin_id":          str,
        "diversity_method": str,
        "snapshot_time":    ISO8601 str,
        "source":           str,

        # Shared concentration metrics (populated when applicable)
        "top_1_pct":        float | None,
        "top_10_pct":       float | None,
        "top_100_pct":      float | None,
        "gini":             float | None,
        "hhi":              float | None,

        # Method-specific fields
        "nakamoto_coefficient": int | None,   # hashrate + validator
        "insider_pct":          float | None, # vesting
        "circulating_ratio":    float | None, # vesting
        "holder_count":         int | None,   # token_holders
    }
"""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Routing table: diversity_method → sub-collector module fetch function
# Imported lazily to avoid hard failures when optional deps (requests, etc.) missing
def _get_collector(method: str):
    if method == "token_holders":
        from .token_holders.collector import fetch
        return fetch
    if method == "hashrate":
        from .btc_hashrate.collector import fetch
        return fetch
    if method == "validator":
        from .eth_validators.collector import fetch
        return fetch
    if method == "vesting":
        from .vesting.collector import fetch
        return fetch
    return None


def _not_implemented_result(coin_id: str) -> dict:
    """
    Return a mid-level placeholder result for coins whose decentralization
    method is not yet implemented.

    The scorer maps ``diversity_method = "not_implemented"`` to a neutral
    17 / 35 pts security score rather than 0, ensuring these coins receive
    a fair automated rating until proper data is available.
    """
    return {
        "coin_id":          coin_id,
        "diversity_method": "not_implemented",
        "snapshot_time":    datetime.now(timezone.utc).isoformat(),
        "source":           "placeholder",
        "note":             "Decentralization method not yet implemented — mid-level placeholder score applied.",
    }


def fetch(coin: dict, config: dict) -> Optional[dict]:
    """
    Route to the correct sub-collector based on coin["diversity_method"].

    Args:
        coin:   Coin config dict (see module docstring for shape).
        config: App config dict with API keys:
                {
                    "COVALENT_API_KEY":  str,
                    "RATED_API_KEY":     str,   # optional
                }

    Returns:
        Standardised result dict, or None on failure.
    """
    coin_id = coin.get("coin_id", "?")
    method  = coin.get("diversity_method", "token_holders")

    # Mid-level placeholder for coins not yet implemented
    if method == "not_implemented":
        logger.info(f"[DecentralizationRisk] {coin_id} → method=not_implemented (placeholder)")
        return _not_implemented_result(coin_id)

    collector = _get_collector(method)
    if collector is None:
        logger.error(f"[DecentralizationRisk] Unknown diversity_method '{method}' for {coin_id}")
        return None

    logger.info(f"[DecentralizationRisk] {coin_id} → method={method}")
    try:
        result = collector(coin, config)
        if result:
            result["diversity_method"] = method
        return result
    except Exception as exc:
        logger.exception(f"[DecentralizationRisk] {coin_id} collector raised: {exc}")
        return None


# Convenience: map coin_id → diversity_method for all known coins.
# The orchestrator can use this if the coins table doesn't yet have the column.
# NOTE: The canonical version of this map lives in coin_registry.DIVERSITY_METHOD_MAP.
#       This copy exists only as a fallback for legacy callers.
try:
    from ..coin_registry import DIVERSITY_METHOD_MAP as COIN_METHOD_MAP
except Exception:
    # Fallback if registry is unavailable
    COIN_METHOD_MAP: dict[str, str] = {
        "bitcoin": "hashrate", "ethereum": "validator",
        "solana": "vesting", "chainlink": "token_holders",
    }


def get_method_for_coin(coin_id: str) -> str:
    """Return the diversity_method for a coin_id, defaulting to 'not_implemented'."""
    return COIN_METHOD_MAP.get(coin_id, "not_implemented")
