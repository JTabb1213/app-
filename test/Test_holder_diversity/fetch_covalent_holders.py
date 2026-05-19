#!/usr/bin/env python3
"""
Covalent Token Holder Diversity Fetcher
Uses Covalent API (https://www.covalenthq.com) — free tier, multi-chain,
supports EVM token holder lists directly.

Get a free API key at: https://www.covalenthq.com/platform/auth/register/
"""

import os
import requests
from pathlib import Path
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Config & env loader
# ─────────────────────────────────────────────────────────────────────────────

def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


ROOT = Path(__file__).resolve().parents[2]
load_env_file(ROOT / "backend" / ".env")
load_env_file(ROOT / ".env")

COVALENT_API_KEY = os.getenv("COVALENT_API_KEY")

COVALENT_BASE_URL = "https://api.covalenthq.com/v1"

# ─────────────────────────────────────────────────────────────────────────────
# Token list — ERC-20 tokens from your coin_aliases.json that have known
# Ethereum contract addresses. Covalent needs (chain_id, contract_address).
# Native coins (BTC, SOL, ADA, etc.) are NOT ERC-20 tokens and cannot be
# looked up this way — use the dedicated fetchers for those.
# ─────────────────────────────────────────────────────────────────────────────
TOKENS = [
    # coin_id (matches coin_aliases.json)  symbol   chain_id  contract_address
    {"coin_id": "chainlink",          "symbol": "LINK",  "chain_id": 1,  "contract": "0x514910771af9ca656af840dff83e8264ecf986ca"},
    {"coin_id": "uniswap",            "symbol": "UNI",   "chain_id": 1,  "contract": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984"},
    {"coin_id": "aave",               "symbol": "AAVE",  "chain_id": 1,  "contract": "0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9"},
    {"coin_id": "shiba-inu",          "symbol": "SHIB",  "chain_id": 1,  "contract": "0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce"},
    {"coin_id": "pepe",               "symbol": "PEPE",  "chain_id": 1,  "contract": "0x6982508145454ce325ddbe47a25d4ec3d2311933"},
    {"coin_id": "lido-dao",           "symbol": "LDO",   "chain_id": 1,  "contract": "0x5a98fcbea516cf06857215779fd812ca3bef1b32"},
    {"coin_id": "the-graph",          "symbol": "GRT",   "chain_id": 1,  "contract": "0xc944e90c64b2c07662a292be6244bdf05cda44a7"},
    {"coin_id": "curve-dao-token",    "symbol": "CRV",   "chain_id": 1,  "contract": "0xd533a949740bb3306d119cc777fa900ba034cd52"},
    {"coin_id": "loopring",           "symbol": "LRC",   "chain_id": 1,  "contract": "0xbbbbca6a901c926f240b89eacb641d8aec7aeafd"},
    {"coin_id": "basic-attention-token", "symbol": "BAT","chain_id": 1,  "contract": "0x0d8775f648430679a709e98d2b0cb6250d2887ef"},
    {"coin_id": "sushi",              "symbol": "SUSHI", "chain_id": 1,  "contract": "0x6b3595068778dd592e39a122f4f5a5cf09c90fe2"},
    {"coin_id": "yearn-finance",      "symbol": "YFI",   "chain_id": 1,  "contract": "0x0bc529c00c6401aef6d220be8c6ea1667f6ad93e"},
    {"coin_id": "decentraland",       "symbol": "MANA",  "chain_id": 1,  "contract": "0x0f5d2fb29fb7d3cfee444a200298f468908cc942"},
    {"coin_id": "the-sandbox",        "symbol": "SAND",  "chain_id": 1,  "contract": "0x3845badade8e6dff049820680d1f14bd3903a5d0"},
    {"coin_id": "ocean-protocol",     "symbol": "OCEAN", "chain_id": 1,  "contract": "0x967da4048cd07ab37855c090aaf366e4ce1b9f48"},
    {"coin_id": "immutable-x",        "symbol": "IMX",   "chain_id": 1,  "contract": "0xf57e7e7c23978c3caec3c3548e3d615c346e79ff"},
    {"coin_id": "havven",             "symbol": "SNX",   "chain_id": 1,  "contract": "0xc011a73ee8576fb46f5e1c5751ca3b9fe0af2a6f"},
    {"coin_id": "compound-governance-token", "symbol": "COMP", "chain_id": 1, "contract": "0xc00e94cb662c3520282e6f5717214004a7f26888"},
]


# ─────────────────────────────────────────────────────────────────────────────
# API
# ─────────────────────────────────────────────────────────────────────────────

def fetch_token_holders(chain_id: int, contract: str, page_size: int = 1000) -> Optional[list]:
    """
    Fetch top token holders via Covalent.
    Endpoint: GET /v1/{chain_id}/tokens/{contract}/token_holders_v2/
    """
    url = f"{COVALENT_BASE_URL}/{chain_id}/tokens/{contract}/token_holders_v2/"
    params = {
        "page-size": page_size,
        "page-number": 0,
    }
    headers = {
        "Authorization": f"Bearer {COVALENT_API_KEY}",
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        print(f"  📡 Raw response keys: {list(data.keys())}")

        if data.get("error"):
            print(f"  ⚠ Covalent error:")
            print(f"     error_code={data.get('error_code')}")
            print(f"     error_message={data.get('error_message')}")
            return None

        items = data.get("data", {}).get("items", [])
        return items

    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return None


def calculate_metrics(holders: list) -> Optional[dict]:
    if not holders:
        return None

    balances = []
    for h in holders:
        try:
            balances.append(int(h.get("balance", 0)))
        except (ValueError, TypeError):
            continue

    balances.sort(reverse=True)
    total = sum(balances)
    if total == 0:
        return None

    n = len(balances)
    top_1_pct   = balances[0]         / total * 100 if n >= 1   else 0
    top_10_pct  = sum(balances[:10])  / total * 100 if n >= 10  else 0
    top_100_pct = sum(balances[:100]) / total * 100 if n >= 100 else 0
    # Gini: must sort ASCENDING for the standard formula → result in [0, 1]
    balances_asc = sorted(balances)
    gini = (2 * sum((i + 1) * b for i, b in enumerate(balances_asc))) / (n * total) - (n + 1) / n
    hhi  = sum((b / total) ** 2 for b in balances)

    return {
        "holder_count": n,
        "top_1_pct":   round(top_1_pct, 2),
        "top_10_pct":  round(top_10_pct, 2),
        "top_100_pct": round(top_100_pct, 2),
        "gini": round(gini, 4),
        "hhi":  round(hhi, 4),
        "top_10_holders": [
            {
                "rank": i + 1,
                "address": holders[i].get("address", "N/A"),
                "pct": round(balances[i] / total * 100, 2),
            }
            for i in range(min(10, n))
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 80)
    print("Covalent Token Holder Diversity Fetcher")
    print("=" * 80)

    for info in TOKENS:
        symbol = info["symbol"]
        print(f"\n📊 {symbol}")
        print(f"   Contract: {info['contract']}")
        print("-" * 80)

        holders = fetch_token_holders(info["chain_id"], info["contract"])
        if holders is None:
            print(f"  ❌ Skipping {symbol}.")
            continue

        print(f"  ✅ Fetched {len(holders)} holders")
        m = calculate_metrics(holders)

        if m:
            print(f"\n  📈 Metrics:")
            print(f"     Holder count:   {m['holder_count']}")
            print(f"     Top 1 holder:   {m['top_1_pct']}%")
            print(f"     Top 10 holders: {m['top_10_pct']}%")
            print(f"     Top 100 holders:{m['top_100_pct']}%")
            print(f"     Gini:           {m['gini']}")
            print(f"     HHI:            {m['hhi']}")
            print(f"\n  🏆 Top 10 addresses:")
            for h in m["top_10_holders"]:
                print(f"     #{h['rank']:2d} {h['address']}  {h['pct']}%")
        else:
            print("  ❌ Could not compute metrics.")

    print("\n" + "=" * 80)
    print("Done!")
    print("=" * 80)


if __name__ == "__main__":
    if not COVALENT_API_KEY:
        print("❌ COVALENT_API_KEY not set.")
        print("   1. Sign up free at https://www.covalenthq.com/platform/auth/register/")
        print("   2. Copy your API key")
        print("   3. Add COVALENT_API_KEY=<key> to backend/.env")
        exit(1)

    main()

