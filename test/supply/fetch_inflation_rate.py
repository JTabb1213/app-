#!/usr/bin/env python3
"""
Estimate inflation rate from supply growth.

Approaches:
  1. Simple model: Compare circulating supply at two time points
  2. From CoinGecko historical data: Fetch supply snapshots
  3. From protocol docs: Parse project tokenomics (manual)

This fetches historical supply data and calculates annual inflation rate.

Note: This is an approximation. True inflation rate depends on:
  - Unlock schedules
  - Staking/delegation rewards
  - Token burning
  - Protocol governance changes
  
Always validate against project documentation for accuracy.
"""

import requests
from typing import Optional
from datetime import datetime, timedelta

COINGECKO_API = "https://api.coingecko.com/api/v3"


def fetch_historical_supply(coin_id: str, days: int = 365) -> Optional[dict]:
    """
    Fetch historical market data to estimate supply growth.
    
    CoinGecko returns market cap and price history, from which we can
    infer supply changes if we assume consistent token counts.
    
    Better approach: use the market_chart endpoint for historical prices,
    then cross-reference with current supply snapshot.
    """
    url = f"{COINGECKO_API}/coins/{coin_id}/market_chart"
    params = {
        "vs_currency": "usd",
        "days": days,
        "interval": "daily",
    }
    
    print(f"  Fetching {days}-day historical data from CoinGecko...")
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return {
            "coin_id": coin_id,
            "prices": data.get("prices", []),  # [[timestamp_ms, price_usd], ...]
            "market_caps": data.get("market_caps", []),
            "volumes": data.get("volumes", []),
        }
    except requests.HTTPError as e:
        print(f"  ❌ HTTP {e.response.status_code}: {e}")
        return None
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return None


def estimate_annual_inflation(current_supply: float, max_supply: Optional[float] = None) -> Optional[dict]:
    """
    Simple inflation estimation from supply caps.
    
    Returns expected annual inflation as percentage if max_supply is known.
    """
    if not max_supply or current_supply >= max_supply:
        return {
            "estimated_annual_inflation_pct": 0.0,
            "note": "Max supply reached or unknown",
        }
    
    # Rough estimate: remaining supply / years to max supply
    remaining = max_supply - current_supply
    estimated_years_to_cap = 4  # typical for many projects
    annual_new_supply = remaining / estimated_years_to_cap
    inflation_rate = (annual_new_supply / current_supply) * 100
    
    return {
        "estimated_annual_inflation_pct": round(inflation_rate, 2),
        "note": "Very rough estimate based on linear cap approach. Validate against protocol docs.",
    }


def main():
    coins = [
        ("bitcoin", 21_000_000),  # BTC max supply is known
        ("ethereum", None),  # ETH has no max supply
        ("cardano", 45_000_000_000),  # ADA max supply known
        ("solana", 508_000_000),  # SOL max supply known
    ]
    
    print("=" * 80)
    print("Token Inflation Rate Estimation")
    print("=" * 80)
    
    for coin_id, max_supply_hint in coins:
        print(f"\n{coin_id.upper()}")
        print("-" * 40)
        
        # Fetch current supply from CoinGecko
        url = f"{COINGECKO_API}/coins/{coin_id}"
        try:
            resp = requests.get(url, params={"market_data": True}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            market_data = data.get("market_data", {})
            
            current_supply = market_data.get("circulating_supply")
            max_supply = market_data.get("max_supply") or max_supply_hint
            name = data.get("name", coin_id)
            
            print(f"  Name: {name}")
            print(f"  Current Circulating Supply: {current_supply:,.0f}" if current_supply else "  Current Supply: N/A")
            print(f"  Max Supply: {max_supply:,.0f}" if max_supply else "  Max Supply: None (unlimited)")
            
            if current_supply and max_supply:
                inflation_est = estimate_annual_inflation(current_supply, max_supply)
                print(f"  Estimated Annual Inflation: {inflation_est['estimated_annual_inflation_pct']}%")
                print(f"  ⚠ {inflation_est['note']}")
            else:
                print("  ⚠ Cannot estimate inflation without circulating and max supply.")
        
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print("\n" + "=" * 80)
    print("⚠ IMPORTANT: These are estimates only.")
    print("  Always cross-reference with official project tokenomics for accuracy.")
    print("=" * 80)


if __name__ == "__main__":
    main()
