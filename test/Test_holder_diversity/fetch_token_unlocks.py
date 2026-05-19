#!/usr/bin/env python3
"""
Token Unlock / Vesting Schedule Fetcher
========================================
For newer L1s (SOL, ADA, AVAX, NEAR, etc.) and many tokens, the REAL
decentralization risk is not richlist concentration — it's KNOWN UPCOMING
UNLOCKS of insider/VC/foundation allocations.

Why this matters more than richlist for newer coins:
  Example: If a16z holds 100M SOL tokens that unlock over 4 years,
  that's a known, scheduled dump risk. The richlist might not even show
  this correctly if tokens are still in a vesting contract.

  The key question: "What % of supply is controlled by insiders,
  and when does it unlock?"

Sources (all free):
  1. token.unlocks.app — free API with vesting schedule data
  2. CoinGecko /coins/{id} — has basic tokenomics (% to team, VC, etc.)
  3. Messari — best data but mostly paywalled
  4. Project's own tokenomics docs / whitepaper data (hardcoded as fallback)

This file tests all three approaches and shows you what data is actually
available for your target coins.
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime, timezone

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

COINGECKO_KEY = os.getenv("COINGECKO_API_KEY") or os.getenv("CG_API_KEY", "")

# ---------------------------------------------------------------------------
# Source 1: token.unlocks.app  (free, no key)
# ---------------------------------------------------------------------------

def fetch_token_unlocks(coin_slug: str) -> dict | None:
    """
    Fetch vesting unlock schedule from token.unlocks.app.
    coin_slug: e.g. "solana", "avalanche-2", "cardano"
    Returns structured unlock schedule or None.
    """
    url = f"https://token.unlocks.app/api/projects/{coin_slug}"
    headers = {"Accept": "application/json", "User-Agent": "CryptoRating/1.0"}
    print(f"  [token.unlocks.app] Fetching: {coin_slug}...")
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code == 404:
            print(f"    ⚠  Not found on token.unlocks.app")
            return None
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"    ⚠  token.unlocks.app failed: {e}")
        return None


def fetch_unlocks_upcoming(coin_slug: str) -> list | None:
    """
    Fetch upcoming scheduled unlock events from token.unlocks.app.
    """
    url = f"https://token.unlocks.app/api/projects/{coin_slug}/upcoming"
    headers = {"Accept": "application/json", "User-Agent": "CryptoRating/1.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Source 2: CoinGecko tokenomics
# ---------------------------------------------------------------------------

def fetch_coingecko_tokenomics(coin_id: str) -> dict | None:
    """
    Fetch tokenomics data from CoinGecko: total supply, circulating supply,
    max supply, and (on pro tier) allocation breakdown.
    
    Even on free tier, supply ratios are useful:
      circulating / total_supply = % of supply already in market
      If circulating << total, large unlocks are still coming.
    """
    base = "https://pro-api.coingecko.com/api/v3" if COINGECKO_KEY else "https://api.coingecko.com/api/v3"
    headers = {}
    if COINGECKO_KEY:
        headers["x-cg-pro-api-key"] = COINGECKO_KEY

    url = f"{base}/coins/{coin_id}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false"
    print(f"  [CoinGecko] Fetching tokenomics for {coin_id}...")
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        md = data.get("market_data", {})
        return {
            "name":                data.get("name"),
            "symbol":              data.get("symbol", "").upper(),
            "circulating_supply":  md.get("circulating_supply"),
            "total_supply":        md.get("total_supply"),
            "max_supply":          md.get("max_supply"),
            "ath":                 md.get("ath", {}).get("usd"),
            "genesis_date":        data.get("genesis_date"),
            "categories":          data.get("categories", [])[:5],
        }
    except Exception as e:
        print(f"    ⚠  CoinGecko failed for {coin_id}: {e}")
        return None


# ---------------------------------------------------------------------------
# Source 3: Hardcoded research data (public knowledge fallback)
# Sourced from: Messari, Binance Research, project whitepapers, foundation disclosures
# ---------------------------------------------------------------------------

KNOWN_TOKENOMICS = {
    "solana": {
        "name": "Solana",
        "symbol": "SOL",
        "source": "Messari/Binance Research (public)",
        "initial_supply_breakdown": {
            "seed_sale":         0.158,   # 15.8% — early backers (FTX, Multicoin, etc.)
            "founding_sale":     0.125,   # 12.5% — early community sale
            "team":              0.125,   # 12.5% — Solana Labs team
            "foundation":        0.104,   # 10.4% — Solana Foundation
            "validator_rewards": 0.380,   # 38% — inflation rewards to validators
            "community":         0.108,   # 10.8% — ecosystem/grants
        },
        "vesting_notes": (
            "Most insider allocations had 2-4 year linear vesting starting 2020. "
            "Major unlocks completed by 2024. FTX estate (~10M SOL) still being "
            "sold off via court-ordered auctions. Ongoing inflation ~5% annually "
            "tapering to 1.5% over ~10 years."
        ),
        "risk_flags": [
            "FTX estate liquidations ongoing — known market overhang",
            "High initial VC concentration (a16z, Multicoin, FTX)",
            "Inflation schedule means continuous dilution",
        ],
    },
    "avalanche": {
        "name": "Avalanche",
        "symbol": "AVAX",
        "source": "Ava Labs tokenomics doc (public)",
        "initial_supply_breakdown": {
            "private_sale":      0.0975,  # 9.75% — private investors
            "public_sale_a":     0.02,    # 2%   — public sale A
            "public_sale_b":     0.005,   # 0.5% — public sale B
            "team_and_options":  0.10,    # 10%  — team (4-year vest)
            "foundation":        0.09,    # 9%   — Ava Labs Foundation
            "strategic_partners":0.05,    # 5%   — partnerships
            "staking_rewards":   0.50,    # 50%  — staking incentives (10yr)
            "testnet_incentives":0.0975,  # 9.75%— early community
            "airdrop":           0.025,   # 2.5% — community airdrop
        },
        "vesting_notes": (
            "Team tokens: 4-year vest, 1-year cliff (started Sept 2020). "
            "Foundation: unlocked over time for ecosystem grants. "
            "Staking rewards: distributed over 10 years on a fixed schedule."
        ),
        "risk_flags": [
            "50% of supply reserved for staking rewards = significant inflation pressure",
            "Team + foundation = 19% — moderate insider concentration",
        ],
    },
    "cardano": {
        "name": "Cardano",
        "symbol": "ADA",
        "source": "IOHK/CF public disclosures",
        "initial_supply_breakdown": {
            "sale_to_backers":   0.576,   # 57.6% — public sale (Japan primarily)
            "iohk":              0.112,   # 11.2% — IOHK (development company)
            "emurgo":            0.028,   # 2.8%  — Emurgo (commercial arm)
            "cardano_foundation":0.028,   # 2.8%  — Cardano Foundation
            "remaining_reserve": 0.256,   # 25.6% — in the reserve, distributed as staking rewards
        },
        "vesting_notes": (
            "No traditional vesting cliffs. IOHK/Emurgo/CF allocations were "
            "distributed at genesis (2017). Reserve ADA is released via staking "
            "rewards at ~0.3% per epoch (~5 days). Relatively low insider concentration "
            "compared to other major L1s."
        ),
        "risk_flags": [
            "IOHK, Emurgo, CF received ~14% combined at genesis with no lockup",
            "Reserve emissions add ~4% annual inflation",
            "Charles Hoskinson (IOHK) has significant personal holdings (undisclosed amount)",
        ],
    },
    "bitcoin": {
        "name": "Bitcoin",
        "symbol": "BTC",
        "source": "Public knowledge / on-chain research",
        "initial_supply_breakdown": {
            "satoshi_era_coins":  0.05,   # ~5% — estimated unmoved early miner coins incl. Satoshi
            "lost_coins_est":     0.15,   # ~15% — estimated permanently lost
            "long_term_holders":  0.60,   # ~60% — held >1 year (HODL supply)
            "exchange_held":      0.12,   # ~12% — on exchanges (CryptoQuant estimate)
            "active_circulation": 0.08,   # ~8% — actively traded
        },
        "vesting_notes": (
            "No vesting. All BTC is mined — there are no insider allocations or "
            "founder premines. The 'Satoshi coins' (~1M BTC, never moved since 2009) "
            "are the only known large concentrated holding. Bitcoin has the most "
            "equitable initial distribution of any major cryptocurrency."
        ),
        "risk_flags": [
            "Satoshi's ~1M BTC: if ever moved, would signal loss of keys or deliberate dump",
            "Early miner concentration: ~5% in wallets from 2009-2010",
            "Mining pool concentration (hashrate) is the real decentralization concern",
        ],
    },
}


def print_known_tokenomics(coin_key: str) -> None:
    data = KNOWN_TOKENOMICS.get(coin_key)
    if not data:
        print(f"    No hardcoded data for {coin_key}")
        return

    print(f"\n  📋 {data['name']} ({data['symbol']}) — Known Tokenomics")
    print(f"     Source: {data['source']}")
    print(f"\n     Initial Supply Breakdown:")
    for category, pct in data["initial_supply_breakdown"].items():
        bar = "█" * int(pct * 40)
        print(f"       {category:<25s} {pct*100:5.1f}%  {bar}")

    # Compute insider concentration
    insider_keys = {"seed_sale", "founding_sale", "team", "foundation",
                    "iohk", "emurgo", "cardano_foundation", "private_sale",
                    "team_and_options", "strategic_partners"}
    insider_pct = sum(v for k, v in data["initial_supply_breakdown"].items()
                     if k in insider_keys) * 100

    print(f"\n     🔴 Insider/VC/Foundation total: ~{insider_pct:.1f}% of initial supply")
    print(f"\n     📝 Vesting Notes:")
    for line in data["vesting_notes"].split(". "):
        if line.strip():
            print(f"       • {line.strip()}.")

    print(f"\n     ⚠  Risk Flags:")
    for flag in data["risk_flags"]:
        print(f"       • {flag}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

COINS_TO_TEST = [
    # (display_name, coingecko_id, token_unlocks_slug, known_tokenomics_key)
    ("Solana",    "solana",      "solana",    "solana"),
    ("Avalanche", "avalanche-2", "avalanche", "avalanche"),
    ("Cardano",   "cardano",     "cardano",   "cardano"),
    ("Bitcoin",   "bitcoin",     None,        "bitcoin"),
]


def main():
    print("=" * 80)
    print("Token Unlock / Vesting / Insider Concentration — Multi-source")
    print("For rating systems, THIS is more relevant than richlist for newer L1s.")
    print("=" * 80)

    for display_name, cg_id, unlocks_slug, known_key in COINS_TO_TEST:
        print(f"\n{'─'*80}")
        print(f"  🪙  {display_name}")
        print(f"{'─'*80}")

        # Source 1: token.unlocks.app
        if unlocks_slug:
            unlock_data = fetch_token_unlocks(unlocks_slug)
            if unlock_data:
                print(f"  ✅ token.unlocks.app data:")
                # Print top-level keys so we know what structure we get
                for k, v in unlock_data.items():
                    if isinstance(v, (str, int, float, bool)):
                        print(f"     {k}: {v}")
                    elif isinstance(v, list):
                        print(f"     {k}: [{len(v)} items]")
                    elif isinstance(v, dict):
                        print(f"     {k}: {{...{len(v)} keys}}")

                upcoming = fetch_unlocks_upcoming(unlocks_slug)
                if upcoming:
                    print(f"\n  📅 Upcoming Unlock Events:")
                    events = upcoming if isinstance(upcoming, list) else upcoming.get("data", [])
                    for event in events[:5]:
                        date   = event.get("date") or event.get("timestamp") or "N/A"
                        amount = event.get("amount") or event.get("tokens") or "N/A"
                        cat    = event.get("category") or event.get("name") or "N/A"
                        pct    = event.get("percentUnlocked") or event.get("pct") or ""
                        pct_str = f"  ({pct}%)" if pct else ""
                        print(f"     {date}  {cat:<20s}  {amount}{pct_str}")

        # Source 2: CoinGecko supply ratio
        cg_data = fetch_coingecko_tokenomics(cg_id)
        if cg_data:
            circ  = cg_data.get("circulating_supply") or 0
            total = cg_data.get("total_supply") or 0
            mx    = cg_data.get("max_supply")
            if circ and total and total > 0:
                unlocked_ratio = circ / total * 100
                print(f"\n  📊 CoinGecko Supply Ratio:")
                print(f"     Circulating:  {circ:>20,.0f}")
                print(f"     Total supply: {total:>20,.0f}")
                if mx:
                    print(f"     Max supply:   {mx:>20,.0f}")
                print(f"     → {unlocked_ratio:.1f}% of total supply is circulating")
                if unlocked_ratio < 50:
                    print(f"     ⚠  Less than 50% circulating — significant unlock overhang remains")
                elif unlocked_ratio < 75:
                    print(f"     ℹ  Moderate unlock overhang remaining")
                else:
                    print(f"     ✅ Most supply already circulating — lower unlock risk")

        # Source 3: Hardcoded known data
        print_known_tokenomics(known_key)

    print("\n" + "=" * 80)
    print("  💡 For your rating system — suggested scoring:")
    print("     Insider/VC % < 10%  → +2 points (very decentralized like BTC)")
    print("     Insider/VC % 10-20% → +1 point  (moderate like AVAX)")
    print("     Insider/VC % 20-35% → 0 points  (high like SOL early stage)")
    print("     Insider/VC % > 35%  → -1 point  (red flag)")
    print("     Large upcoming unlock (>2% supply in next 90d) → -1 point")
    print("=" * 80)


if __name__ == "__main__":
    main()
