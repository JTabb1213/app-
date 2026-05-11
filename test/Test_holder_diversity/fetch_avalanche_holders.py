#!/usr/bin/env python3
"""
Avalanche (AVAX) Holder Diversity Fetcher
Uses Covalent API with WAVAX (Wrapped AVAX) as a proxy.

Requires the same COVALENT_API_KEY already used by fetch_covalent_holders.py.
  Add to backend/.env:  COVALENT_API_KEY=your_key_here

Why WAVAX?
  Blockchair does not support Avalanche C-Chain on its free tier.
  Native AVAX richlist is not available via any free public API.
  WAVAX (Wrapped AVAX, an ERC-20 on Avalanche C-Chain) is an excellent proxy:
    - Contract: 0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7
    - Users wrap AVAX 1:1 to use it in DeFi, making the largest holders
      representative of the largest AVAX holders overall.

Docs: https://www.covalenthq.com/docs/api/
"""

import os
import math
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

COVALENT_API_KEY     = os.getenv("COVALENT_API_KEY", "")
COVALENT_BASE        = "https://api.covalenthq.com/v1"
AVAX_CHAIN_ID        = "43114"  # Avalanche C-Chain
WAVAX_CONTRACT       = "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7"
WAVAX_DECIMALS       = 18
FETCH_LIMIT          = 100  # per page


def fetch_wavax_holders(pages: int = 3) -> Optional[list]:
    """
    Fetch the top WAVAX token holders via Covalent.
    Returns a list of holder dicts from the API.
    """
    all_items: list = []
    for page in range(0, pages):
        url = (
            f"{COVALENT_BASE}/{AVAX_CHAIN_ID}/tokens/"
            f"{WAVAX_CONTRACT}/token_holders_v2/"
        )
        params = {
            "page-number": page,
            "page-size":   FETCH_LIMIT,
        }
        print(f"  Fetching WAVAX holders page {page + 1}/{pages}...")
        try:
            resp = requests.get(
                url, params=params,
                auth=(COVALENT_API_KEY, ""),
                timeout=20,
            )
            if resp.status_code == 501:
                print(f"  ❌ 501 Not Implemented — Covalent free tier may not support chain {AVAX_CHAIN_ID}.")
                return None
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
                "rank":          i + 1,
                "address":       holders[i].get("address", "N/A"),
                "balance_wavax": round(balances[i] / 10 ** WAVAX_DECIMALS, 4),
                "pct":           round(balances[i] / total * 100, 2),
            }
            for i in range(min(10, n))
        ],
    }


def main():
    print("=" * 80)
    print("Avalanche (AVAX) Holder Diversity — Covalent API (WAVAX proxy)")
    print("WAVAX contract: " + WAVAX_CONTRACT)
    print("NOTE: WAVAX holders are used as a proxy for native AVAX distribution.")
    print("=" * 80)
    holders = fetch_wavax_holders(pages=3)
    if not holders:
        print("❌ Could not fetch WAVAX holders.")
        return
    print(f"  ✅ Fetched {len(holders)} WAVAX holders")
    m = calculate_metrics(holders)
    if m:
        print(f"\n  📈 Metrics (top {m['holder_count']} WAVAX holders):")
        print(f"     Top 1 holder:    {m['top_1_pct']}%")
        print(f"     Top 10 holders:  {m['top_10_pct']}%")
        print(f"     Top 100 holders: {m['top_100_pct']}%")
        print(f"     Gini:            {m['gini']}")
        print(f"     HHI:             {m['hhi']}")
        print(f"\n  🏆 Top 10 WAVAX holders:")
        for h in m["top_10"]:
            print(f"     #{h['rank']:2d} {h['address']}  {h['balance_wavax']} WAVAX  ({h['pct']}%)")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    if not COVALENT_API_KEY:
        print("❌ COVALENT_API_KEY not set in backend/.env")
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


load_env_file(ROOT / "backend" / ".env")

BLOCKCHAIR_API_KEY = os.getenv("BLOCKCHAIR_API_KEY")
BLOCKCHAIR_BASE = "https://api.blockchair.com"


def fetch_avax_richlist(limit: int = 1000) -> Optional[list]:
    """
    Fetch the top Avalanche C-Chain addresses by native AVAX balance.
    Balances are returned in nAVAX (1 AVAX = 1,000,000,000 nAVAX).
    """
    url = f"{BLOCKCHAIR_BASE}/avalanche/addresses"
    params = {
        "s": "balance(desc)",
        "limit": limit,
    }
    if BLOCKCHAIR_API_KEY:
        params["key"] = BLOCKCHAIR_API_KEY

    print(f"  Fetching top {limit} AVAX C-Chain addresses from Blockchair...")
    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        if "data" not in data:
            print(f"  ⚠ Unexpected response: {list(data.keys())}")
            print(f"  Raw: {data}")
            return None

        return data["data"]

    except requests.HTTPError as e:
        print(f"  ❌ HTTP error: {e.response.status_code} — {e}")
        print(f"  Note: Blockchair may not support Avalanche on free tier.")
        print(f"  Alternative: Use Snowtrace (https://snowtrace.io/api) for AVAX C-Chain data.")
        return None
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return None


def calculate_metrics(addresses: list) -> Optional[dict]:
    balances = []
    for row in addresses:
        try:
            balances.append(int(row.get("balance", 0)))
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

    # nAVAX → AVAX: divide by 1e9
    return {
        "holder_count": n,
        "top_1_pct":    round(top_1_pct, 2),
        "top_10_pct":   round(top_10_pct, 2),
        "top_100_pct":  round(top_100_pct, 2),
        "gini":         round(gini, 4),
        "hhi":          round(hhi, 4),
        "top_10_addresses": [
            {
                "rank":         i + 1,
                "address":      addresses[i].get("address", "N/A"),
                "balance_avax": round(balances[i] / 1e9, 4),
                "pct":          round(balances[i] / total * 100, 2),
            }
            for i in range(min(10, n))
        ],
    }


def main():
    print("=" * 80)
    print("Avalanche (AVAX) Holder Diversity")
    print("Source: Blockchair API — C-Chain native AVAX balances")
    print("=" * 80)

    addresses = fetch_avax_richlist(limit=1000)
    if not addresses:
        print("❌ Could not fetch AVAX addresses.")
        return

    print(f"  ✅ Fetched {len(addresses)} addresses")
    m = calculate_metrics(addresses)

    if m:
        print(f"\n  📈 Metrics (from top {m['holder_count']} richlist addresses):")
        print(f"     Top 1 holder:    {m['top_1_pct']}%")
        print(f"     Top 10 holders:  {m['top_10_pct']}%")
        print(f"     Top 100 holders: {m['top_100_pct']}%")
        print(f"     Gini:            {m['gini']}")
        print(f"     HHI:             {m['hhi']}")
        print(f"\n  🏆 Top 10 addresses:")
        for h in m["top_10_addresses"]:
            print(f"     #{h['rank']:2d} {h['address']}  {h['balance_avax']} AVAX  ({h['pct']}%)")
    else:
        print("  ❌ Could not compute metrics.")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
