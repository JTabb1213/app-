#!/usr/bin/env python3
"""
Bitcoin Hashrate / Miner Decentralization
==========================================
For Bitcoin, "holder diversity" is the wrong frame entirely.
The analogous decentralization metric is HASHRATE DISTRIBUTION.

Why hashrate matters:
  Bitcoin is Proof-of-Work. Miners compete to find blocks.
  Whoever controls the most hashing power controls:
    - Which transactions get confirmed (censorship risk)
    - The ability to execute a 51% attack (double-spend)
  
  If 3 mining pools control >50% of hashrate → 51% attack is theoretically
  possible with collusion. This is the REAL centralization risk for BTC.

Key metrics:
  - Pool concentration: top 3/10 pools % of hashrate
  - Nakamoto Coefficient: min pools to reach 51%
  - Unknown miners %: hashrate not attributed to any known pool

Data sources (all free, no key required):
  - mempool.space API — real-time pool stats, no auth required
  - blockchain.com mining stats — public
  - btc.com pool stats — public

Note: "Mining pools" are themselves decentralized — pool operators don't
actually own the hashrate, individual miners do. So even if one pool has
35% of hashrate, the individual miners could switch pools at any time.
This is why pool concentration is a SOFTER risk than it appears.
"""

import requests
from datetime import datetime, timezone

BASE_MEMPOOL = "https://mempool.space/api/v1"


def fetch_mining_pools(days: int = 1) -> list | None:
    """
    Fetch mining pool hashrate distribution from mempool.space.
    days: 1, 3, 7, or 30 — time window for hashrate measurement.
    Returns list of pools with name and blockCount (proxy for hashrate share).
    """
    url = f"{BASE_MEMPOOL}/mining/pools/{days}d"
    print(f"  Fetching BTC mining pool stats ({days}d window) from mempool.space...")
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        pools = data.get("pools", [])
        print(f"  ✅ Got {len(pools)} pools (from last {days} day(s) of blocks)")
        return pools
    except Exception as e:
        print(f"  ⚠  mempool.space failed: {e}")
        return None


def fetch_hashrate_history() -> dict | None:
    """
    Fetch total network hashrate (EH/s) over time.
    Useful for trend: is hashrate growing (more miners = more decentralized)?
    """
    url = f"{BASE_MEMPOOL}/mining/hashrate/3m"
    print("  Fetching hashrate history (3 months) from mempool.space...")
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        hashrates = data.get("hashrates", [])
        if hashrates:
            latest = hashrates[-1]
            avg_30 = sum(h["avgHashrate"] for h in hashrates[-30:]) / min(30, len(hashrates))
            return {
                "latest_hashrate_eh": round(latest["avgHashrate"] / 1e18, 2),
                "avg_30d_hashrate_eh": round(avg_30 / 1e18, 2),
                "data_points": len(hashrates),
            }
    except Exception as e:
        print(f"  ⚠  Hashrate history failed: {e}")
    return None


def fetch_recent_blocks(limit: int = 144) -> list | None:
    """
    Fetch the last N blocks to cross-check pool attribution.
    144 blocks ≈ 1 day of Bitcoin blocks (1 block per ~10 min).
    """
    url = f"{BASE_MEMPOOL}/blocks"
    print(f"  Fetching last {limit} blocks from mempool.space...")
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  ⚠  Block fetch failed: {e}")
        return None


def compute_concentration_metrics(pools: list) -> dict:
    """
    Compute decentralization metrics from pool hashrate shares.
    Uses blockCount as a proxy for hashrate (proportional over same window).
    """
    weights = sorted(
        [float(p.get("blockCount", 0)) for p in pools if p.get("blockCount", 0) > 0],
        reverse=True
    )
    weights_asc = sorted(weights)

    if not weights:
        return {}

    total = sum(weights)
    n = len(weights)

    top_1_pct  = weights[0]       / total * 100
    top_3_pct  = sum(weights[:3]) / total * 100
    top_10_pct = sum(weights[:10])/ total * 100 if n >= 10 else sum(weights) / total * 100

    # Gini (ascending sort)
    gini = (2 * sum((i + 1) * b for i, b in enumerate(weights_asc))) / (n * total) - (n + 1) / n
    hhi  = sum((b / total) ** 2 for b in weights)

    # Nakamoto: min pools to collude for 51% attack
    cumulative = 0
    nakamoto = 0
    for w in weights:
        cumulative += w
        nakamoto += 1
        if cumulative / total > 0.51:
            break

    # Unknown miners: blocks not attributed to any named pool
    unknown = next((p for p in pools if p.get("name", "").lower() in ("unknown", "other", "")), None)
    unknown_pct = unknown.get("blockCount", 0) / total * 100 if unknown else 0.0

    return {
        "pool_count":      n,
        "top_1_pct":       round(top_1_pct, 2),
        "top_3_pct":       round(top_3_pct, 2),
        "top_10_pct":      round(top_10_pct, 2),
        "gini":            round(gini, 4),
        "hhi":             round(hhi, 4),
        "nakamoto_51pct":  nakamoto,
        "unknown_pct":     round(unknown_pct, 2),
    }


def main():
    print("=" * 80)
    print("Bitcoin (BTC) Miner / Hashrate Decentralization — mempool.space API")
    print("NOTE: This measures MINING POWER concentration, not wallet ownership.")
    print("      Pools don't own the hashrate — individual miners can switch pools.")
    print("=" * 80)

    # Fetch 1-day and 7-day windows
    pools_1d = fetch_mining_pools(days=1)
    pools_7d = fetch_mining_pools(days=7)

    hashrate_info = fetch_hashrate_history()
    if hashrate_info:
        print(f"\n  ⚡ Network Hashrate:")
        print(f"     Latest:     {hashrate_info['latest_hashrate_eh']} EH/s")
        print(f"     30d avg:    {hashrate_info['avg_30d_hashrate_eh']} EH/s")

    for label, pools in [("1 Day", pools_1d), ("7 Days", pools_7d)]:
        if not pools:
            continue
        m = compute_concentration_metrics(pools)
        if not m:
            continue

        print(f"\n  📈 Hashrate Concentration ({label} window, {m['pool_count']} pools):")
        print(f"     Top 1 pool:   {m['top_1_pct']}%")
        print(f"     Top 3 pools:  {m['top_3_pct']}%")
        print(f"     Top 10 pools: {m['top_10_pct']}%")
        print(f"     Gini:         {m['gini']}")
        print(f"     HHI:          {m['hhi']}")
        print(f"     Nakamoto (51%): {m['nakamoto_51pct']} pools needed for 51% attack")
        print(f"     Unknown miner blocks: {m['unknown_pct']}%")

        print(f"\n  🏆 Top 10 Pools ({label}):")
        pools_sorted = sorted(pools, key=lambda p: p.get("blockCount", 0), reverse=True)
        total_blocks = sum(p.get("blockCount", 0) for p in pools)
        for i, p in enumerate(pools_sorted[:10]):
            name   = p.get("name") or p.get("poolId") or "Unknown"
            blocks = p.get("blockCount", 0)
            pct    = blocks / total_blocks * 100 if total_blocks else 0
            slug   = p.get("slug") or ""
            print(f"     #{i+1:2d} {name:<25s}  {blocks:4d} blocks  ({pct:.1f}%)")

    print("\n" + "=" * 80)
    print("  💡 For your rating system:")
    print("     - Nakamoto coefficient ≥ 3 → healthy (need 3+ pools to attack)")
    print("     - Nakamoto coefficient = 2 → yellow flag")
    print("     - Nakamoto coefficient = 1 → red flag (one pool ≥ 51%)")
    print("     - Unknown miner % > 20% → good (means decentralized solo miners)")
    print("     - Note: pool concentration overstates risk since miners can switch")
    print("=" * 80)


if __name__ == "__main__":
    main()
