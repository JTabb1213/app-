#!/usr/bin/env python3
"""
Combined supply metrics fetcher.

Fetches and displays:
  - Circulating Supply
  - Max Supply
  - Total Supply
  - Inflation Rate (estimated)
  - Price and Market Cap

Reads all 50 coins from data/coin_aliases.json and fetches in batches to avoid
rate limiting. CoinGecko allows up to 250 coins per request.

Useful for quickly evaluating tokenomics for a coin.
"""

import json
import requests
from pathlib import Path
from typing import Optional

COINGECKO_API = "https://api.coingecko.com/api/v3"
COINS_FILE = Path(__file__).resolve().parents[2] / "data" / "coin_aliases.json"


def fetch_full_supply_metrics(coin_ids: list) -> Optional[list]:
    """Fetch complete supply metrics for multiple coins in one request.
    
    CoinGecko allows up to 250 coin IDs per request, so we batch them.
    """
    all_results = []
    batch_size = 250
    
    for i in range(0, len(coin_ids), batch_size):
        batch = coin_ids[i:i + batch_size]
        ids_str = ",".join(batch)
        url = f"{COINGECKO_API}/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": ids_str,
            "order": "market_cap_desc",
            "per_page": len(batch),
            "page": 1,
            "sparkline": False,
        }
        
        try:
            print(f"  Fetching batch {i//batch_size + 1} ({len(batch)} coins)...")
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            coins = resp.json()
            
            for coin in coins:
                circ = coin.get("circulating_supply")
                max_s = coin.get("max_supply")
                
                # Estimate inflation
                inflation = None
                if circ and max_s and max_s > circ:
                    remaining = max_s - circ
                    inflation = (remaining / max_s) * 100  # % of supply left to issue
                
                all_results.append({
                    "id": coin.get("id", ""),
                    "name": coin.get("name", ""),
                    "symbol": coin.get("symbol", "").upper(),
                    "circulating_supply": circ,
                    "total_supply": coin.get("total_supply"),
                    "max_supply": max_s,
                    "price_usd": coin.get("current_price"),
                    "market_cap_usd": coin.get("market_cap"),
                    "supply_inflation_potential_pct": inflation,
                })
        except Exception as e:
            print(f"  ❌ Error fetching batch: {e}")
            return None
    
    return all_results


def calculate_concentration(circ: float, max_s: Optional[float]) -> Optional[dict]:
    """Simple supply concentration metrics."""
    if not circ or not max_s:
        return None
    
    pct_issued = (circ / max_s) * 100
    pct_remaining = 100 - pct_issued
    
    return {
        "pct_supply_issued": round(pct_issued, 2),
        "pct_supply_remaining": round(pct_remaining, 2),
    }


def main():
    # Load all coins from coin_aliases.json
    if not COINS_FILE.exists():
        print(f"❌ Coins file not found: {COINS_FILE}")
        return
    
    with open(COINS_FILE) as f:
        aliases_data = json.load(f)
    
    coin_ids = list(aliases_data.get("assets", {}).keys())
    if not coin_ids:
        print("❌ No coins found in coin_aliases.json")
        return
    
    print("=" * 100)
    print(f"SUPPLY METRICS SUMMARY — CoinGecko API (Batched) — {len(coin_ids)} coins")
    print("=" * 100)
    print()
    
    # Fetch all coins in batches
    metrics_list = fetch_full_supply_metrics(coin_ids)
    if not metrics_list:
        print("❌ Failed to fetch supply data")
        return
    
    print()
    for metrics in metrics_list:
        circ = metrics["circulating_supply"]
        total = metrics["total_supply"]
        max_s = metrics["max_supply"]
        price = metrics["price_usd"]
        mcap = metrics["market_cap_usd"]
        inflation = metrics["supply_inflation_potential_pct"]
        
        print(f"\n{metrics['name']} ({metrics['symbol']})")
        print("─" * 100)
        
        if circ:
            print(f"  Circulating Supply:        {circ:>20,.0f}")
        else:
            print(f"  Circulating Supply:        {'N/A':>20}")
        
        if total:
            print(f"  Total Supply:              {total:>20,.0f}")
        else:
            print(f"  Total Supply:              {'N/A':>20}")
        
        if max_s:
            print(f"  Max Supply:                {max_s:>20,.0f}")
            if circ and max_s:
                conc = calculate_concentration(circ, max_s)
                if conc:
                    print(f"    → {conc['pct_supply_issued']}% issued, {conc['pct_supply_remaining']}% remaining")
        else:
            print(f"  Max Supply:                {'∞ (unlimited)':>20}")
        
        if inflation is not None:
            print(f"  Inflation Potential:       {inflation:>19.2f}%")
        
        if price:
            print(f"  Current Price:             ${price:>19,.2f}")
        
        if mcap:
            print(f"  Market Cap:                ${mcap:>19,.0f}")
    
    print("\n" + "=" * 100)
    print("NOTES:")
    print("  • Fetched in 1 API call (batched) — no rate limiting")
    print("  • Inflation Potential = % of max supply yet to be issued (linear assumption)")
    print("  • Real inflation depends on unlock schedules, staking rewards, burns, etc.")
    print("  • Always validate against official tokenomics documentation")
    print("=" * 100)


if __name__ == "__main__":
    main()
