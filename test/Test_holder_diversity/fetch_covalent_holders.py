#!/usr/bin/env python3
"""
Covalent Token Holder Diversity Fetcher
Uses Covalent API (https://www.covalenthq.com) — free tier, multi-chain,
supports EVM token holder lists directly.

Get a free API key at: https://www.covalenthq.com/platform/auth/register/
"""

import os
import requests
import json
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

CHAIN_IDS = {
    "ethereum": 1,
    "polygon": 137,
    "bsc": 56,
    "avalanche": 43114,
    "arbitrum": 42161,
    "optimism": 10,
    "base": 8453,
}

COINS_PATH = ROOT / "rating" / "holder-diversity-collector" / "coins.json"


def load_coin_list(path: Path) -> list:
    if not path.exists():
        raise FileNotFoundError(f"coins.json not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_token_list(coins: list) -> list:
    tokens = []
    for coin in coins:
        symbol = coin.get("coin_id", "?").upper()
        contract = coin.get("contract_address")
        chain = coin.get("chain", "ethereum")
        chain_id = CHAIN_IDS.get(chain)
        if chain_id is None:
            print(f"  ⚠ Skipping unknown chain '{chain}' for {symbol}")
            continue
        if not contract:
            print(f"  ⚠ Skipping {symbol}: contract_address missing")
            continue

        tokens.append({
            "symbol": symbol,
            "contract": contract.lower(),
            "chain_id": chain_id,
        })
    return tokens


TOKENS = build_token_list(load_coin_list(COINS_PATH))


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
    top_1_pct  = balances[0]    / total * 100 if n >= 1   else 0
    top_10_pct = sum(balances[:10])  / total * 100 if n >= 10  else 0
    top_100_pct = sum(balances[:100]) / total * 100 if n >= 100 else 0
    gini = (2 * sum((i + 1) * b for i, b in enumerate(balances))) / (n * total) - (n + 1) / n
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

