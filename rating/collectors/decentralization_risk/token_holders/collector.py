"""
Token Holder Concentration — Covalent collector
=================================================
Fetches top ERC-20 / EVM token holders via the Covalent API and computes
concentration metrics (top-N %, Gini, HHI).

Used for: ERC-20 tokens on Ethereum and other EVM chains.
NOT used for: native L1 coins (BTC, ETH, SOL, ADA, etc.).

Config keys used:
    config["COVALENT_API_KEY"]
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# Covalent chain slug by chain_id
_CHAIN_SLUGS = {
    1:     "eth-mainnet",
    137:   "matic-mainnet",
    56:    "bsc-mainnet",
    43114: "avalanche-mainnet",
    42161: "arbitrum-mainnet",
    10:    "optimism-mainnet",
    8453:  "base-mainnet",
}

FETCH_LIMIT = 100
BASE_URL    = os.getenv("COVALENT_API_BASE_URL", "https://api.covalenthq.com/v1")



def _compute_metrics(balances: list[int]) -> dict:
    """Compute concentration metrics from a list of raw token balances."""
    if not balances or sum(balances) == 0:
        return {}
    n     = len(balances)
    total = sum(balances)
    desc  = sorted(balances, reverse=True)
    asc   = sorted(balances)

    top_1   = desc[0]         / total * 100
    top_10  = sum(desc[:10])  / total * 100
    top_100 = sum(desc[:100]) / total * 100
    gini    = (2 * sum((i + 1) * b for i, b in enumerate(asc))) / (n * total) - (n + 1) / n
    hhi     = sum((b / total) ** 2 for b in desc)

    return {
        "holder_count": n,
        "top_1_pct":    round(top_1, 2),
        "top_10_pct":   round(top_10, 2),
        "top_100_pct":  round(top_100, 2),
        "gini":         round(gini, 4),
        "hhi":          round(hhi, 4),
    }


def fetch(coin: dict, config: dict) -> Optional[dict]:
    """
    Fetch token holder concentration for an EVM token via Covalent.

    Args:
        coin:   Must contain "coin_id". "chain" and "contract_address" are read
                from evm_contracts.json if not provided in the coin dict.
        config: Must contain "COVALENT_API_KEY".

    Returns:
        Standardised decentralization result dict, or None on failure.
    """
    api_key = config.get("COVALENT_API_KEY", "")
    if not api_key:
        logger.error("[TokenHolders] COVALENT_API_KEY not set")
        return None
    logger.debug(f"[TokenHolders] Using key ending ...{api_key[-4:]}")

    coin_id = coin["coin_id"]

    # Resolve contract info — prefer coin dict fields, fall back to CoinRegistry
    contract = coin.get("contract_address") or ""
    chain_id = coin.get("chain_id")  # set by CoinRegistry for token_holders coins
    if not contract or chain_id is None:
        from ...coin_registry import EVM_CONTRACTS
        info = EVM_CONTRACTS.get(coin_id)
        if not info:
            logger.warning(f"[TokenHolders] No contract address found for '{coin_id}'")
            return None
        contract = info["contract"]
        chain_id = info["chain_id"]

    if chain_id not in _CHAIN_SLUGS:
        logger.warning(f"[TokenHolders] Unsupported chain_id {chain_id} for '{coin_id}'")
        return None

    url     = f"{BASE_URL}/{chain_id}/tokens/{contract}/token_holders_v2/"
    headers = {"Authorization": f"Bearer {api_key}"}
    params  = {"page-size": FETCH_LIMIT, "page-number": 0}
    logger.info(f"[TokenHolders] {coin_id}: key={'SET('+api_key[-4:]+')' if api_key else 'EMPTY'} url={url}")
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        if not resp.ok:
            logger.error(f"[TokenHolders] {coin_id}: HTTP {resp.status_code} — body: {resp.text[:500]}")
            resp.raise_for_status()
        data = resp.json()
        if data.get("error"):
            logger.error(f"[TokenHolders] {coin_id}: {data.get('error_message')}")
            return None

        items = data.get("data", {}).get("items", [])
        if not items:
            return None

        balances = sorted(
            [int(h["balance"]) for h in items if h.get("balance") and int(h["balance"]) > 0],
            reverse=True,
        )
        metrics = _compute_metrics(balances)
        if not metrics:
            return None

        total = sum(balances)
        return {
            "coin_id":          coin_id,
            "source":           "covalent",
            "snapshot_time":    datetime.now(timezone.utc).isoformat(),
            "chain":            _CHAIN_SLUGS.get(chain_id, str(chain_id)),
            "contract_address": contract,
            **metrics,
            # method-specific fields set to None for schema consistency
            "nakamoto_coefficient": None,
            "insider_pct":          None,
            "circulating_ratio":    None,
            "top_holders": [
                {
                    "rank":    i + 1,
                    "address": items[i].get("address", ""),
                    "pct":     round(balances[i] / total * 100, 4) if total else 0,
                }
                for i in range(min(10, len(items)))
            ],
        }
    except Exception as exc:
        logger.exception(f"[TokenHolders] {coin_id} raised: {exc}")
        return None
