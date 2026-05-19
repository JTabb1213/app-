#!/usr/bin/env python3
"""
Ethereum Validator Decentralization — rated.network API
=========================================================
This is a BETTER signal than richlist data for ETH because it measures
consensus power concentration, not token ownership.

Why this matters:
  The risk with ETH isn't that one wallet holds a lot of ETH.
  It's that one ENTITY (like Lido) controls a large % of validators,
  meaning they have outsized influence over which transactions get included
  and finalized. This is the actual decentralization risk.

Key metrics:
  - Nakamoto Coefficient: minimum # of entities that could collude to
    control 33% of stake (attack threshold). Higher = more decentralized.
  - Client diversity: what % of validators run each software client.
    If 90% run one client and it has a bug, the whole network is at risk.
  - Entity concentration: top 10 staking entities % of total stake.

API: https://rated.network  (free, no key required for public endpoints)
Docs: https://docs.rated.network/
"""

import os
import requests
from pathlib import Path

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

RATED_API_KEY = os.getenv("RATED_API_KEY", "")  # Optional — increases rate limits
BASE_URL = "https://api.rated.network/v0"


def get_headers() -> dict:
    h = {"Accept": "application/json", "User-Agent": "CryptoRating/1.0"}
    if RATED_API_KEY:
        h["Authorization"] = f"Bearer {RATED_API_KEY}"
    return h


def fetch_network_overview() -> dict | None:
    """
    Fetch overall Ethereum network stats: total validators, total stake, etc.
    """
    url = f"{BASE_URL}/eth/network/overview"
    print("  Fetching ETH network overview from rated.network...")
    try:
        resp = requests.get(url, headers=get_headers(), timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  ⚠  Network overview failed: {e}")
        return None


def fetch_entity_concentration(size: int = 20) -> list | None:
    """
    Fetch the top staking entities and their % of total stake.
    These are named entities: Lido, Coinbase, Binance, etc.
    This is the KEY metric — named entities, not anonymous wallets.
    """
    url = f"{BASE_URL}/eth/operators?size={size}&sortOrder=desc&sortKey=avgValidatorEffectiveness"
    print(f"  Fetching top {size} staking entities from rated.network...")
    try:
        resp = requests.get(url, headers=get_headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", data) if isinstance(data, dict) else data
    except Exception as e:
        print(f"  ⚠  Entity fetch failed: {e}")
        return None


def fetch_client_diversity() -> dict | None:
    """
    Fetch client diversity — what % of validators run each ETH client.
    Prysm, Lighthouse, Teku, Nimbus, etc.
    Critical: if one client dominates, a single software bug can cause mass slashing.
    """
    url = f"{BASE_URL}/eth/clients"
    print("  Fetching client diversity from rated.network...")
    try:
        resp = requests.get(url, headers=get_headers(), timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  ⚠  Client diversity fetch failed: {e}")
        return None


def fetch_p2p_network_stats() -> dict | None:
    """
    Fetch P2P / geographic decentralization if available.
    """
    url = f"{BASE_URL}/eth/network/stats"
    try:
        resp = requests.get(url, headers=get_headers(), timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def compute_concentration_metrics(entities: list) -> dict:
    """
    Compute Gini and top-N concentration from entity stake shares.
    Much more meaningful than richlist since these are NAMED entities.
    """
    # Try to get validatorCount or activeStake as the weight
    weights = []
    for e in entities:
        w = (e.get("validatorCount") or
             e.get("activeStake") or
             e.get("totalStake") or
             e.get("stake") or 0)
        weights.append(float(w))

    weights = [w for w in weights if w > 0]
    if not weights:
        return {}

    weights_desc = sorted(weights, reverse=True)
    weights_asc  = sorted(weights)
    total = sum(weights_desc)
    n = len(weights_desc)

    top_1_pct  = weights_desc[0]       / total * 100
    top_3_pct  = sum(weights_desc[:3]) / total * 100
    top_10_pct = sum(weights_desc[:10])/ total * 100

    gini = (2 * sum((i + 1) * b for i, b in enumerate(weights_asc))) / (n * total) - (n + 1) / n
    hhi  = sum((b / total) ** 2 for b in weights_desc)

    # Nakamoto coefficient: min entities to control >33% stake
    cumulative = 0
    nakamoto_33 = 0
    for w in weights_desc:
        cumulative += w
        nakamoto_33 += 1
        if cumulative / total > 0.33:
            break

    return {
        "entity_count":  n,
        "top_1_pct":     round(top_1_pct, 2),
        "top_3_pct":     round(top_3_pct, 2),
        "top_10_pct":    round(top_10_pct, 2),
        "gini":          round(gini, 4),
        "hhi":           round(hhi, 4),
        "nakamoto_33pct": nakamoto_33,
    }


def main():
    print("=" * 80)
    print("Ethereum (ETH) Validator Decentralization — rated.network")
    print("NOTE: This measures CONSENSUS POWER concentration, not token ownership.")
    print("      Named entities (Lido, Coinbase, etc.) — not anonymous wallets.")
    if not RATED_API_KEY:
        print("  ⚠  No RATED_API_KEY set. Using unauthenticated (lower rate limits).")
        print("     Free key at: https://www.rated.network/")
    print("=" * 80)

    # 1. Network overview
    overview = fetch_network_overview()
    if overview:
        total_validators = overview.get("validatorCount") or overview.get("totalValidators", "N/A")
        total_stake = overview.get("activeStake") or overview.get("totalStake", "N/A")
        print(f"\n  🌐 Network Overview:")
        print(f"     Total validators: {total_validators:,}" if isinstance(total_validators, int) else f"     Total validators: {total_validators}")
        if isinstance(total_stake, (int, float)):
            print(f"     Total staked ETH: {total_stake / 1e18:,.0f} ETH" if total_stake > 1e15 else f"     Total staked:    {total_stake:,.0f}")
        print(f"     Raw overview keys: {list(overview.keys())}")
    else:
        print("\n  ⚠  Could not fetch network overview")

    # 2. Entity concentration
    entities = fetch_entity_concentration(size=20)
    if entities:
        print(f"\n  ✅ Fetched {len(entities)} staking entities")
        metrics = compute_concentration_metrics(entities)
        if metrics:
            print(f"\n  📈 Staking Entity Concentration (top {metrics['entity_count']} entities):")
            print(f"     Top 1 entity:     {metrics['top_1_pct']}%")
            print(f"     Top 3 entities:   {metrics['top_3_pct']}%")
            print(f"     Top 10 entities:  {metrics['top_10_pct']}%")
            print(f"     Gini:             {metrics['gini']}")
            print(f"     HHI:              {metrics['hhi']}")
            print(f"     Nakamoto (33%):   {metrics['nakamoto_33pct']} entities needed to reach 33% stake")

        print(f"\n  🏆 Top 10 Staking Entities:")
        for i, e in enumerate(entities[:10]):
            name = e.get("displayName") or e.get("name") or e.get("operatorTag") or e.get("id", "Unknown")
            validators = e.get("validatorCount") or e.get("activeStake") or "N/A"
            effectiveness = e.get("avgValidatorEffectiveness") or e.get("effectiveness") or "N/A"
            if isinstance(validators, (int, float)) and isinstance(overview, dict):
                total_v = overview.get("validatorCount", 0)
                pct = f"  ({validators/total_v*100:.2f}%)" if total_v else ""
            else:
                pct = ""
            eff_str = f"  eff={effectiveness:.1f}%" if isinstance(effectiveness, float) else ""
            print(f"     #{i+1:2d} {name:<30s} {validators:>8}{pct}{eff_str}")
    else:
        print("\n  ⚠  Could not fetch entity data — showing raw API response structure")
        # Try a simpler endpoint to see what's available
        try:
            resp = requests.get(f"{BASE_URL}/eth/operators?size=5", headers=get_headers(), timeout=15)
            print(f"     Status: {resp.status_code}")
            print(f"     Response: {resp.text[:500]}")
        except Exception as e:
            print(f"     Error: {e}")

    # 3. Client diversity
    clients = fetch_client_diversity()
    if clients:
        print(f"\n  💻 Client Diversity (critical for network safety):")
        client_list = clients if isinstance(clients, list) else clients.get("data", [])
        for c in client_list:
            name = c.get("client") or c.get("name", "Unknown")
            pct  = c.get("percentage") or c.get("share") or c.get("pct") or "N/A"
            if isinstance(pct, float):
                print(f"     {name:<15s} {pct:.1f}%")
            else:
                print(f"     {name:<15s} {pct}")

    print("\n" + "=" * 80)
    print("  💡 For your rating system:")
    print("     - Use Nakamoto Coefficient as the primary decentralization score")
    print("     - Penalize if top 1 entity > 25% stake (Lido risk)")
    print("     - Penalize if client diversity < 2 dominant clients")
    print("=" * 80)


if __name__ == "__main__":
    main()
