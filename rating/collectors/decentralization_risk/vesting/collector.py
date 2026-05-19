"""
Insider / Vesting Concentration — static research data + CoinGecko collector
==============================================================================
For newer PoS L1s (SOL, ADA, AVAX, NEAR, etc.), the primary decentralization
risk is insider/VC/foundation allocation, not wallet richlist concentration.

Two data sources:
  1. KNOWN_TOKENOMICS — hardcoded research data from public disclosures
     (Messari, Binance Research, project whitepapers). Updated manually.
  2. CoinGecko — circulating / total supply ratio (auto-fetched).

Why this matters:
  A coin where VCs hold 40% of supply (still vesting) is fundamentally more
  risky than the richlist shows, because vesting contracts don't appear
  prominently in wallet rankings until unlock.

Config keys used:
    config["COINGECKO_API_KEY"]   (optional — increases rate limits)
"""

import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

import requests

logger  = logging.getLogger(__name__)
TIMEOUT = 15

# ─────────────────────────────────────────────────────────────────────────────
# Static research data — sourced from public disclosures
# insider_pct = sum of seed/team/foundation/VC allocations at genesis
# ─────────────────────────────────────────────────────────────────────────────
KNOWN_TOKENOMICS: dict[str, dict] = {
    "solana": {
        "insider_pct": 51.2,   # seed 15.8% + founding 12.5% + team 12.5% + foundation 10.4%
        "source":      "Messari / Binance Research",
        "risk_flags":  ["FTX estate liquidations ongoing", "High VC concentration (a16z, Multicoin)"],
    },
    "avalanche-2": {
        "insider_pct": 33.8,   # private 9.75% + team 10% + foundation 9% + partners 5%
        "source":      "Ava Labs tokenomics doc",
        "risk_flags":  ["50% staking reward inflation over 10yr", "Team + foundation = 19%"],
    },
    "cardano": {
        "insider_pct": 16.8,   # IOHK 11.2% + Emurgo 2.8% + CF 2.8%
        "source":      "IOHK / CF public disclosures",
        "risk_flags":  ["No lockup on genesis allocations", "Reserve emissions ~4% annual inflation"],
    },
    "polkadot": {
        "insider_pct": 30.0,   # Web3 Foundation ~30% at genesis
        "source":      "Web3 Foundation public disclosures",
        "risk_flags":  ["Web3 Foundation holds large treasury", "Parachain slot auction model"],
    },
    "near": {
        "insider_pct": 36.5,   # NEAR Foundation 10% + team 14% + investors 12.5%
        "source":      "NEAR Foundation tokenomics",
        "risk_flags":  ["Foundation has large undistributed grant allocation"],
    },
    "aptos": {
        "insider_pct": 51.0,   # core contributors 19% + foundation 16.5% + investors 13.5%
        "source":      "Aptos Foundation tokenomics doc",
        "risk_flags":  ["Very high insider concentration — relatively new coin"],
    },
    "sui": {
        "insider_pct": 52.0,   # Mysten Labs + investors + Sui Foundation
        "source":      "Mysten Labs tokenomics doc",
        "risk_flags":  ["Majority still vesting", "Mysten Labs team holds large allocation"],
    },
    "cosmos": {
        "insider_pct": 20.0,   # Tendermint team + ICF
        "source":      "Cosmos / ICF public disclosures",
        "risk_flags":  ["ICF large undisclosed holdings"],
    },
    "tron": {
        "insider_pct": 34.0,   # Justin Sun / TRX Foundation
        "source":      "TRX whitepaper / public research",
        "risk_flags":  ["Justin Sun controls large allocation and foundation"],
    },
    "hedera-hashgraph": {
        "insider_pct": 40.0,   # Hedera council + founding team
        "source":      "Hedera tokenomics disclosure",
        "risk_flags":  ["Council model — 39 known entities control governance"],
    },
    "the-open-network": {
        "insider_pct": 20.0,   # TON Foundation
        "source":      "TON Foundation public disclosures",
        "risk_flags":  ["TON Foundation controls large treasury"],
    },
}


# Delay between individual CoinGecko calls to stay within free-tier rate limit.
# Free tier = 30 req/min.  Other collectors use quota too, so be conservative.
_CG_DELAY = float(os.environ.get("VESTING_CG_DELAY", "2.5"))


def _fetch_coingecko_supply(coin_id: str, api_key: str) -> Optional[dict]:
    """Fetch circulating/total supply ratio from CoinGecko.

    Supports three modes:
      - No key:        public API (very low rate limit)
      - Demo key:      public API + x-cg-demo-api-key header (30 req/min)
      - Pro key:       pro-api endpoint  + x-cg-pro-api-key header
    """
    is_pro  = api_key and not api_key.startswith("CG-")  # pro keys don't start with CG-
    base    = "https://pro-api.coingecko.com/api/v3" if is_pro else "https://api.coingecko.com/api/v3"
    headers = {}
    if is_pro:
        headers["x-cg-pro-api-key"] = api_key
    elif api_key:
        headers["x-cg-demo-api-key"] = api_key
    url = (
        f"{base}/coins/{coin_id}"
        "?localization=false&tickers=false&market_data=true"
        "&community_data=false&developer_data=false"
    )
    time.sleep(_CG_DELAY)  # rate-limit guard before every call
    try:
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        md   = data.get("market_data", {})
        circ = md.get("circulating_supply")
        total= md.get("total_supply")
        return {
            "circulating_supply": circ,
            "total_supply":       total,
            "circulating_ratio":  round(circ / total, 4) if circ and total and total > 0 else None,
        }
    except Exception as exc:
        logger.warning(f"[Vesting] CoinGecko supply fetch failed for {coin_id}: {exc}")
        return None


def fetch(coin: dict, config: dict) -> Optional[dict]:
    """
    Fetch insider/vesting concentration data for a PoS L1.

    Args:
        coin:   Must contain "coin_id".
        config: May contain "COINGECKO_API_KEY".

    Returns:
        Standardised decentralization result dict, or None on failure.
    """
    coin_id = coin.get("coin_id", "")
    api_key = config.get("COINGECKO_API_KEY", "") or config.get("CG_API_KEY", "")

    known = KNOWN_TOKENOMICS.get(coin_id, {})
    supply_data = _fetch_coingecko_supply(coin_id, api_key)

    # Need at least one of the two sources
    if not known and not supply_data:
        logger.warning(f"[Vesting] No data available for {coin_id}")
        return None

    insider_pct       = known.get("insider_pct")
    circulating_ratio = supply_data.get("circulating_ratio") if supply_data else None

    # Compute a pseudo top_1_pct / top_10_pct from insider_pct as proxy
    # so the scorer can use a unified scoring path when needed
    top_1_pct  = None
    top_10_pct = None
    if insider_pct is not None:
        # Approximate: assume largest single insider entity ≈ insider_pct / 3
        top_1_pct  = round(insider_pct / 3, 2)
        top_10_pct = round(min(insider_pct, 100.0), 2)

    return {
        "coin_id":           coin_id,
        "source":            known.get("source", "CoinGecko"),
        "snapshot_time":     datetime.now(timezone.utc).isoformat(),
        "insider_pct":       insider_pct,
        "circulating_ratio": circulating_ratio,
        "risk_flags":        known.get("risk_flags", []),
        # Proxy concentration values derived from insider allocation
        "top_1_pct":         top_1_pct,
        "top_10_pct":        top_10_pct,
        "top_100_pct":       None,
        "gini":              None,
        "hhi":               None,
        # Not applicable for vesting method
        "holder_count":         None,
        "nakamoto_coefficient": None,
        "top_holders":          [],
    }
