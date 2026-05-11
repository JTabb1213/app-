#!/usr/bin/env python3
"""
Solana (SOL) Holder Diversity Fetcher
Uses the Helius RPC endpoint (getLargestAccounts).

Requires a FREE Helius API key:
  Sign up at https://www.helius.dev/  (free tier: 1M credits/month)
  Add to backend/.env:  HELIUS_API_KEY=your_key_here

Why not public Solana RPC?
  The public endpoint (api.mainnet-beta.solana.com) rate-limits heavily
  and returns only the top 20 accounts. Helius is free and returns more.

RPC docs: https://docs.helius.dev/
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

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}" if HELIUS_API_KEY else ""


def fetch_sol_largest_accounts(filter_type: str = "circulating") -> Optional[list]:
    """
    Fetch the largest SOL accounts.

    filter_type: "circulating" (default) | "nonCirculating"
    Returns list of {address, lamports} dicts.
    1 SOL = 1,000,000,000 lamports.

    Note: Public RPC returns max 20. Helius returns more.
    """
    payload = {
        "jsonrpc": "2.0",
        "id":      1,
        "method":  "getLargestAccounts",
        "params":  [{"filter": filter_type}],
    }

    print(f"  Fetching largest {filter_type} SOL accounts from Solana RPC...")
    try:
        resp = requests.post(RPC_URL, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            print(f"  ❌ RPC error: {data['error']}")
            return None

        return data.get("result", {}).get("value", [])

    except requests.HTTPError as e:
        print(f"  ❌ HTTP error: {e}")
        return None
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return None


def calculate_metrics(accounts: list) -> Optional[dict]:
    # lamports (int)
    balances = sorted([int(a.get("lamports", 0)) for a in accounts], reverse=True)
    total = sum(balances)
    if total == 0:
        return None

    n = len(balances)
    top_1_pct   = balances[0]         / total * 100
    top_10_pct  = sum(balances[:10])  / total * 100 if n >= 10 else sum(balances) / total * 100
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
        "top_10_accounts": [
            {
                "rank":        i + 1,
                "address":     accounts[i].get("address", "N/A"),
                "balance_sol": round(int(accounts[i].get("lamports", 0)) / 1e9, 4),
                "pct":         round(balances[i] / total * 100, 2),
            }
            for i in range(min(10, n))
        ],
    }


def main():
    print("=" * 80)
    print("Solana (SOL) Holder Diversity — Helius RPC (getLargestAccounts)")
    print("=" * 80)

    accounts = fetch_sol_largest_accounts(filter_type="circulating")
    if not accounts:
        print("❌ Could not fetch SOL accounts.")
        return

    print(f"  ✅ Fetched {len(accounts)} accounts")
    m = calculate_metrics(accounts)

    if m:
        print(f"\n  📈 Metrics (from top {m['holder_count']} accounts):")
        print(f"     Top 1 holder:    {m['top_1_pct']}%")
        print(f"     Top 10 holders:  {m['top_10_pct']}%")
        print(f"     Top 100 holders: {m['top_100_pct']}%")
        print(f"     Gini:            {m['gini']}")
        print(f"     HHI:             {m['hhi']}")
        print(f"\n  🏆 Top 10 accounts:")
        for h in m["top_10_accounts"]:
            print(f"     #{h['rank']:2d} {h['address']}  {h['balance_sol']:,.2f} SOL  ({h['pct']}%)")
    else:
        print("  ❌ Could not compute metrics.")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    if not HELIUS_API_KEY:
        print("❌ HELIUS_API_KEY not set.")
        print("   Get a FREE key at: https://www.helius.dev/")
        print("   Then add to backend/.env:  HELIUS_API_KEY=your_key")
        exit(1)
    main()
