#!/usr/bin/env python3
"""
Bitcoin (BTC) Holder Diversity Fetcher
Uses Blockchair API.

⚠ NOTE: Blockchair's sorted address endpoint returns empty data without a key,
  and IPs that have made too many keyless requests get temporarily blocked (430).
  A Blockchair API key is required for reliable results.
  There is currently no free no-signup alternative for a BTC richlist.

  Add to root .env:  BLOCKCHAIR_API_KEY=your_key_here
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
BLOCKCHAIR_API_KEY = os.getenv("BLOCKCHAIR_API_KEY", "")
BLOCKCHAIR_BASE = "https://api.blockchair.com"


def fetch_btc_richlist(limit: int = 100) -> Optional[list]:
    url = f"{BLOCKCHAIR_BASE}/bitcoin/addresses"
    params = {
        "s":     "balance(desc)",
        "limit": limit,
    }
    if BLOCKCHAIR_API_KEY:
        params["key"] = BLOCKCHAIR_API_KEY
    print(f"  Fetching top {limit} BTC addresses from Blockchair...")
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
                "rank":        i + 1,
                "address":     addresses[i].get("address", "N/A"),
                "balance_btc": round(balances[i] / 1e8, 4),
                "pct":         round(balances[i] / total * 100, 2),
            }
            for i in range(min(10, n))
        ],
    }


def main():
    print("=" * 80)
    print("Bitcoin (BTC) Holder Diversity — Blockchair API")
    print("=" * 80)
    rows = fetch_btc_richlist(limit=100)
    if not rows:
        print("❌ Could not fetch BTC addresses.")
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
            print(f"     #{h['rank']:2d} {h['address']}  {h['balance_btc']} BTC  ({h['pct']}%)")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    if not BLOCKCHAIR_API_KEY:
        print("❌ BLOCKCHAIR_API_KEY not set.")
        print("   Blockchair requires a key for BTC richlist data.")
        print("   Add BLOCKCHAIR_API_KEY=your_key to root .env")
        exit(1)
    main()


import os
import requests
import json
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


load_env_file(ROOT / "backend" / ".env")

# Optional: set BLOCKCHAIR_API_KEY in your .env for higher rate limits
BLOCKCHAIR_API_KEY = os.getenv("BLOCKCHAIR_API_KEY")

BLOCKCHAIR_BASE = "https://api.blockchair.com"


def fetch_btc_richlist(limit: int = 1000) -> Optional[list]:
    """
    Fetch the top Bitcoin addresses by balance from Blockchair.
    Returns a list of dicts with 'address' and 'balance' (in satoshis).
    """
    url = f"{BLOCKCHAIR_BASE}/bitcoin/addresses"
    params = {
        "s": "balance(desc)",
        "limit": limit,
    }
    if BLOCKCHAIR_API_KEY:
        params["key"] = BLOCKCHAIR_API_KEY

    print(f"  Fetching top {limit} BTC addresses from Blockchair...")
    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        if "data" not in data:
            print(f"  ⚠ Unexpected response: {list(data.keys())}")
            return None

        return data["data"]

    except requests.HTTPError as e:
        print(f"  ❌ HTTP error: {e}")
        return None
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return None


def calculate_metrics(addresses: list, balance_field: str = "balance") -> Optional[dict]:
    balances = []
    for row in addresses:
        try:
            balances.append(int(row.get(balance_field, 0)))
        except (ValueError, TypeError):
            continue

    balances.sort(reverse=True)
    total = sum(balances)
    if total == 0:
        return None

    n = len(balances)
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
        "top_10_addresses": [
            {
                "rank":    i + 1,
                "address": addresses[i].get("address", "N/A"),
                "balance_btc": round(balances[i] / 1e8, 4),
                "pct":    round(balances[i] / total * 100, 2),
            }
            for i in range(min(10, n))
        ],
    }


def main():
    print("=" * 80)
    print("Bitcoin (BTC) Holder Diversity")
    print("Source: Blockchair API")
    print("=" * 80)

    addresses = fetch_btc_richlist(limit=1000)
    if not addresses:
        print("❌ Could not fetch BTC addresses.")
        return

    print(f"  ✅ Fetched {len(addresses)} addresses")
    m = calculate_metrics(addresses, balance_field="balance")

    if m:
        print(f"\n  📈 Metrics (from top {m['holder_count']} richlist addresses):")
        print(f"     Top 1 holder:    {m['top_1_pct']}%")
        print(f"     Top 10 holders:  {m['top_10_pct']}%")
        print(f"     Top 100 holders: {m['top_100_pct']}%")
        print(f"     Gini:            {m['gini']}")
        print(f"     HHI:             {m['hhi']}")
        print(f"\n  🏆 Top 10 addresses:")
        for h in m["top_10_addresses"]:
            print(f"     #{h['rank']:2d} {h['address']}  {h['balance_btc']} BTC  ({h['pct']}%)")
    else:
        print("  ❌ Could not compute metrics.")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
