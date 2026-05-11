#!/usr/bin/env python3
"""
Cardano (ADA) Holder Diversity Fetcher
Uses Blockfrost API.

Requires a FREE Blockfrost API key (mainnet):
  Sign up at https://blockfrost.io  (free tier: 50k req/day)
  Add to backend/.env:  BLOCKFROST_PROJECT_ID=mainnetXXXXXXXXX

Approach:
  1. Fetch all stake pools sorted by live_stake (largest pools first).
  2. Fetch the top delegators from each pool in batches.
  3. Collect unique accounts with the largest stakes.

This captures the largest ADA holders in the staking ecosystem (~70-75% of
circulating supply is staked), which is the best free-API approximation of
a true ADA richlist. A full richlist is not available via any free public API.

Docs: https://docs.blockfrost.io/
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

BLOCKFROST_PROJECT_ID = os.getenv("BLOCKFROST_PROJECT_ID", "")
BLOCKFROST_BASE = "https://cardano-mainnet.blockfrost.io/api/v0"
HEADERS = {"project_id": BLOCKFROST_PROJECT_ID}


def _bf_get(path: str, params: dict = None) -> Optional[list | dict]:
    try:
        resp = requests.get(
            f"{BLOCKFROST_BASE}{path}",
            headers=HEADERS,
            params=params or {},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        print(f"  ❌ HTTP {e.response.status_code}: {e}")
        return None
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return None


def fetch_ada_richlist(top_n_pools: int = 10, delegators_per_pool: int = 100) -> Optional[list]:
    """
    Gather top delegators across the largest staking pools.
    Returns a list of dicts: {stake_address, live_stake (lovelace)}.
    """
    # Step 1: get top pools by live_stake
    print(f"  Fetching top staking pools from Blockfrost...")
    pools = _bf_get("/pools", params={"count": top_n_pools, "order": "desc"})
    if not pools:
        return None
    pool_ids = pools[:top_n_pools] if isinstance(pools[0], str) else [p["pool_id"] for p in pools[:top_n_pools]]
    print(f"  Got {len(pool_ids)} pool IDs")

    # Step 2: for each pool, get top delegators
    seen: dict[str, int] = {}
    for pool_id in pool_ids:
        result = _bf_get(f"/pools/{pool_id}/delegators",
                         params={"count": delegators_per_pool, "order": "desc"})
        if not result:
            continue
        for d in result:
            addr = d.get("address") or d.get("stake_address", "")
            stake = int(d.get("live_stake", 0))
            if addr and stake > seen.get(addr, 0):
                seen[addr] = stake

    if not seen:
        return None

    # Sort by live_stake descending
    sorted_accounts = [
        {"stake_address": addr, "total_balance": lovelace}
        for addr, lovelace in sorted(seen.items(), key=lambda x: x[1], reverse=True)
    ]
    print(f"  Collected {len(sorted_accounts)} unique stake accounts")
    return sorted_accounts


def calculate_metrics(accounts: list) -> Optional[dict]:
    balances = []
    for row in accounts:
        try:
            balances.append(int(row.get("total_balance", 0)))
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
                "stake_address": accounts[i].get("stake_address", "N/A"),
                "balance_ada":   round(balances[i] / 1_000_000, 2),
                "pct":           round(balances[i] / total * 100, 2),
            }
            for i in range(min(10, n))
        ],
    }


def main():
    print("=" * 80)
    print("Cardano (ADA) Holder Diversity — Blockfrost API")
    print("NOTE: Approximation via top delegators of largest staking pools.")
    print("      A full ADA richlist is not available via any free public API.")
    print("=" * 80)
    accounts = fetch_ada_richlist(top_n_pools=10, delegators_per_pool=100)
    if not accounts:
        print("❌ Could not fetch ADA accounts.")
        return
    m = calculate_metrics(accounts)
    if m:
        print(f"\n  📈 Metrics (top {m['holder_count']} stake accounts from largest pools):")
        print(f"     Top 1 holder:    {m['top_1_pct']}%")
        print(f"     Top 10 holders:  {m['top_10_pct']}%")
        print(f"     Top 100 holders: {m['top_100_pct']}%")
        print(f"     Gini:            {m['gini']}")
        print(f"     HHI:             {m['hhi']}")
        print(f"\n  🏆 Top 10 stake accounts:")
        for h in m["top_10"]:
            print(f"     #{h['rank']:2d} {h['stake_address']}  {h['balance_ada']:,.2f} ADA  ({h['pct']}%)")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    if not BLOCKFROST_PROJECT_ID:
        print("❌ BLOCKFROST_PROJECT_ID not set.")
        print("   Get a FREE key at: https://blockfrost.io")
        print("   Then add to backend/.env:  BLOCKFROST_PROJECT_ID=mainnetXXXXXXXXX")
        exit(1)
    main()
