#!/usr/bin/env python3
"""
Fetch token supply metrics from CoinGecko.

Retrieves:
  - Circulating Supply
  - Max Supply
  - Total Supply
  - Current Price (for reference)

CoinGecko Free API docs: https://docs.coingecko.com/reference/introduction
No API key required for free tier.
"""

import requests
from typing import Optional

COINGECKO_API = "https://api.coingecko.com/api/v3"


def fetch_supply_data(coin_id: str) -> Optional[dict]:
    """
    Fetch supply metrics for a coin from CoinGecko.
    
    Args:
        coin_id: CoinGecko coin ID (e.g., 'bitcoin', 'ethereum', 'cardano', 'solana')
    
    Returns:
        dict with keys:
          - circulating_supply (int)
          - total_supply (int)
          - max_supply (int or None)
          - current_price_usd (float)
          - market_cap_usd (float)
    """
    url = f"{COINGECKO_API}/coins/{coin_id}"
    params = {
        "localization": False,
        "market_data": True,
        "community_data": False,
        "developer_data": False,
    }
    
    print(f"  Fetching supply data from CoinGecko for {coin_id}...")
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        market_data = data.get("market_data", {})
        return {
            "coin_id": coin_id,
            "name": data.get("name", ""),
            "symbol": data.get("symbol", "").upper(),
            "circulating_supply": market_data.get("circulating_supply"),
            "total_supply": market_data.get("total_supply"),
            "max_supply": market_data.get("max_supply"),
            "current_price_usd": market_data.get("current_price", {}).get("usd"),
            "market_cap_usd": market_data.get("market_cap", {}).get("usd"),
        }
    except requests.HTTPError as e:
        print(f"  ❌ HTTP {e.response.status_code}: {e}")
        return None
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return None


def fetch_multiple_supply_data(coin_ids: list) -> Optional[list]:
    """
    Fetch supply metrics for multiple coins in a single request (more efficient).
    Uses /coins/markets endpoint to batch fetch.
    """
    # Convert coin IDs to comma-separated string
    ids_str = ",".join(coin_ids)
    url = f"{COINGECKO_API}/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": ids_str,
        "order": "market_cap_desc",
        "per_page": len(coin_ids),
        "page": 1,
        "sparkline": False,
    }
    
    print(f"  Fetching supply data for {len(coin_ids)} coins (batched)...")
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        coins = resp.json()
        
        results = []
        for coin in coins:
            results.append({
                "coin_id": coin.get("id", ""),
                "name": coin.get("name", ""),
                "symbol": coin.get("symbol", "").upper(),
                "circulating_supply": coin.get("circulating_supply"),
                "total_supply": coin.get("total_supply"),
                "max_supply": coin.get("max_supply"),
                "current_price_usd": coin.get("current_price"),
                "market_cap_usd": coin.get("market_cap"),
            })
        return results
    except requests.HTTPError as e:
        print(f"  ❌ HTTP {e.response.status_code}: {e}")
        return None
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return None


def main():
    # Test with a few major coins
    coins = ["bitcoin", "ethereum", "cardano", "solana", "ripple"]
    
    print("=" * 80)
    print("Token Supply Data — CoinGecko API (Batched)")
    print("=" * 80)
    
    # Fetch all coins in one request
    results = fetch_multiple_supply_data(coins)
    if not results:
        print("❌ Failed to fetch supply data")
        return
    
    for data in results:
        print(f"\n{data['name']} ({data['symbol']})")
        print(f"  Circulating Supply: {data['circulating_supply']:,.0f}" if data['circulating_supply'] else "  Circulating Supply: N/A")
        print(f"  Total Supply:       {data['total_supply']:,.0f}" if data['total_supply'] else "  Total Supply: N/A")
        print(f"  Max Supply:         {data['max_supply']:,.0f}" if data['max_supply'] else "  Max Supply: N/A (unlimited)")
        print(f"  Price:              ${data['current_price_usd']:,.2f}" if data['current_price_usd'] else "  Price: N/A")
        print(f"  Market Cap:         ${data['market_cap_usd']:,.0f}" if data['market_cap_usd'] else "  Market Cap: N/A")
    
    print("\n" + "=" * 80)
    print(f"Summary: Fetched data for {len(results)} coins in 1 API call")
    print("=" * 80)


if __name__ == "__main__":
    main()
