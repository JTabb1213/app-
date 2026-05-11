#!/usr/bin/env python3
"""
Ethereum (ETH) Native Holder Diversity Fetcher
Uses Covalent API with WETH (Wrapped ETH) as a proxy.

Uses the same COVALENT_API_KEY already in your root .env — no new signup needed.

Why WETH?
  No free public API exposes a sorted native ETH richlist without a paid key.
  WETH (Wrapped ETH, ERC-20 on Ethereum mainnet) is an excellent proxy:
    - Contract: 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2
    - Users wrap ETH 1:1 to use in DeFi, so largest WETH holders are
      representative of the largest ETH holders overall.

Docs: https://www.covalenthq.com/docs/api/
"""

import os
import requests
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


load_env_file(ROOT / ".env")
load_env_file(ROOT / "backend" / ".env")

COVALENT_API_KEY = os.getenv("COVALENT_API_KEY", "")
COVALENT_BASE    = "https://api.covalenthq.com/v1"
ETH_CHAIN_ID     = "1"
WETH_CONTRACT    = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
WETH_DECIMALS    = 18
FETCH_LIMIT      = 100


def fetch_weth_holders(pages: int = 3) -> Optional[list]:
    """Fetch the top WETH token holders via Covalent."""
    all_items: list = []
    for page in range(0, pages):
        url = (
            f"{COVALENT_BASE}/{ETH_CHAIN_ID}/tokens/"
            f"{WETH_CONTRACT}/token_holders_v2/"
        )
        params = {"page-number": page, "page-size": FETCH_LIMIT}
        print(f"  Fetching WETH holders page {page + 1}/{pages}...")
        try:
            resp = requests.get(
                url, params=params,
                auth=(COVALENT_API_KEY, ""),
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data", {}).get("items", [])
            if not items:
                break
            all_items.extend(items)
        except requests.HTTPError as e:
            print(f"  ❌ HTTP {e.response.status_code}: {e}")
            return None
        except Exception as e:
            print(f"  ❌ Exception: {e}")
            return None
    return all_items if all_items else None


def calculate_metrics(holders: list) -> Optional[dict]:
    balances = sorted([int(h.get("balance", 0)) for h in holders], reverse=True)
    total = sum(balances)
    if total == 0:
        return None
    n = len(balances)
    top_1_pct   = balances[0]         / total * 100
    top_10_pct  = sum(balances[:10])  / total * 100 if n >= 10  else sum(balances) / total * 100
    top_100_pct = sum(balances[:100]) / total * 100 if n >= 100 else sum(balances) / total * 100
    gini = (2 * sum((i + 1) * b for i, b in enumerate(balances))) / (n * total) - (n + 1) / n
    hhi  = sum((b / total) ** 2 for b in balances)
    return {
        "holder_count": n,
        "top_1_pct":    round(top_1_pct, 2),
        "top_10_pct":   round(top_10_pct, 2),
        "top_100_pct":  round(top_100_pct, 2),
        "gini":         round(gini, 4),
        "hhi":          round(hhi, 4),
        "top_10": [
            {
                "rank":        i + 1,
                "address":     holders[i].get("address", "N/A"),
                "balance_eth": round(balances[i] / 10 ** WETH_DECIMALS, 4),
                "pct":         round(balances[i] / total * 100, 2),
            }
            for i in range(min(10, n))
        ],
    }


def main():
    print("=" * 80)
    print("Ethereum (ETH) Holder Diversity — Covalent API (WETH proxy)")
    print("WETH contract: " + WETH_CONTRACT)
    print("NOTE: WETH holders used as proxy for native ETH distribution.")
    print("=" * 80)
    holders = fetch_weth_holders(pages=3)
    if not holders:
        print("❌ Could not fetch WETH holders.")
        return
    print(f"  ✅ Fetched {len(holders)} WETH holders")
    m = calculate_metrics(holders)
    if m:
        print(f"\n  📈 Metrics (top {m['holder_count']} WETH holders):")
        print(f"     Top 1 holder:    {m['top_1_pct']}%")
        print(f"     Top 10 holders:  {m['top_10_pct']}%")
        print(f"     Top 100 holders: {m['top_100_pct']}%")
        print(f"     Gini:            {m['gini']}")
        print(f"     HHI:             {m['hhi']}")
        print(f"\n  🏆 Top 10 WETH holders:")
        for h in m["top_10"]:
            print(f"     #{h['rank']:2d} {h['address']}  {h['balance_eth']} WETH  ({h['pct']}%)")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    if not COVALENT_API_KEY:
        print("❌ COVALENT_API_KEY not set in .env")
        exit(1)
    main()


import os
import requests
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


load_env_file(ROOT / ".env")
load_env_file(ROOT / "backend" / ".env")

BLOCKCHAIR_API_KEY = os.getenv("BLOCKCHAIR_API_KEY", "")
BLOCKCHAIR_BASE = "https://api.blockchair.com"


def fetch_eth_richlist(limit: int = 100) -> Optional[list]:
    """
    Fetch the top Ethereum addresses by native ETH balance from Blockchair.
    Balances are returned in Wei.
    """
    url = f"{BLOCKCHAIR_BASE}/ethereum/addresses"
    params = {
        "s":     "balance(desc)",
        "limit": limit,
    }
    if BLOCKCHAIR_API_KEY:
        params["key"] = BLOCKCHAIR_API_KEY
    print(f"  Fetching top {limit} ETH addresses from Blockchair...")
    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        rows = data.get("data", [])
        if not rows:
            print(f"  ⚠ Empty response. Context: {data.get('context', {}).get('error', 'unknown')}")
        return rows
    except requests.HTTPError as e:
        print(f"  ❌ HTTP {e.response.status_code}: {e}")
        return None
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return None


def calculate_metrics(addresses: list) -> Optional[dict]:
    balances = sorted([int(r.get("balance", 0)) for r in addresses], reverse=True)
    total = sum(balances)
    if total == 0:
        return None
    n = len(balances)
    top_1_pct   = balances[0]         / total * 100
    top_10_pct  = sum(balances[:10])  / total * 100 if n >= 10  else sum(balances) / total * 100
    top_100_pct = sum(balances[:100]) / total * 100 if n >= 100 else sum(balances) / total * 100
    gini = (2 * sum((i + 1) * b for i, b in enumerate(balances))) / (n * total) - (n + 1) / n
    hhi  = sum((b / total) ** 2 for b in balances)
    return {
        "holder_count": n,
        "top_1_pct":    round(top_1_pct, 2),
        "top_10_pct":   round(top_10_pct, 2),
        "top_100_pct":  round(top_100_pct, 2),
        "gini":         round(gini, 4),
        "hhi":          round(hhi, 4),
        "top_10": [
            {
                "rank":       i + 1,
                "address":    addresses[i].get("address", "N/A"),
                "balance_eth": round(balances[i] / 1e18, 4),
                "pct":        round(balances[i] / total * 100, 2),
            }
            for i in range(min(10, n))
        ],
    }


def main():
    print("=" * 80)
    print("Ethereum (ETH) Native Holder Diversity — Blockchair API")
    print("NOTE: Native ETH balances only (not ERC-20 token holders).")
    print("=" * 80)
    rows = fetch_eth_richlist(limit=100)
    if not rows:
        print("❌ Could not fetch ETH addresses.")
        return
    print(f"  ✅ Fetched {len(rows)} addresses")
    m = calculate_metrics(rows)
    if m:
        print(f"\n  📈 Metrics (top {m['holder_count']} richlist):")
        print(f"     Top 1 holder:    {m['top_1_pct']}%")
        print(f"     Top 10 holders:  {m['top_10_pct']}%")
        print(f"     Top 100 holders: {m['top_100_pct']}%")
        print(f"     Gini:            {m['gini']}")
        print(f"     HHI:             {m['hhi']}")
        print(f"\n  🏆 Top 10 addresses:")
        for h in m["top_10"]:
            print(f"     #{h['rank']:2d} {h['address']}  {h['balance_eth']} ETH  ({h['pct']}%)")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    if not BLOCKCHAIR_API_KEY:
        print("⚠ BLOCKCHAIR_API_KEY not set — using Blockchair no-key mode up to 1440 requests/day.")
    main()
