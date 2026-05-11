#!/usr/bin/env python3
"""
Etherscan Holder Diversity Fetcher
Demonstrates how to fetch token holder data from Etherscan API.
"""

import os
import requests
import json
import time
from pathlib import Path
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

ETHERSCAN_BASE_URL = "https://api.etherscan.io/v2/api"  # V2 API (V1 is deprecated)


def load_env_file(path: Path, debug: bool = False) -> None:
    """Load key=value pairs from a .env file into os.environ if not already set."""
    if not path.exists():
        if debug:
            print(f"  [DEBUG] .env file not found: {path}")
        return

    if debug:
        print(f"  [DEBUG] Loading .env from: {path}")

    content = path.read_text().splitlines()
    if debug:
        print(f"  [DEBUG] Total lines in file: {len(content)}")

    for i, line in enumerate(content):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            if debug and line:
                print(f"  [DEBUG] Line {i}: skipped (comment or empty)")
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        
        if debug:
            print(f"  [DEBUG] Line {i}: key='{key}', raw_value='{value}'")
        
        # Remove quotes from both ends
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
            if debug:
                print(f"           → stripped quotes: '{value[:20]}...' " if len(value) > 20 else f"           → stripped quotes: '{value}'")

        if key and key not in os.environ:
            os.environ[key] = value
            if debug:
                print(f"           → set in os.environ")
        elif debug and key in os.environ:
            print(f"           → already in os.environ, skipping")


# Attempt to load backend .env first, then repo root .env if necessary.
ROOT = Path(__file__).resolve().parents[2]
DEBUG_ENV = os.getenv("DEBUG_ENV_LOADER") == "1"

if DEBUG_ENV:
    print("[DEBUG] Environment loader starting...")
    print(f"[DEBUG] Script location: {Path(__file__).resolve()}")
    print(f"[DEBUG] Root directory: {ROOT}")

load_env_file(ROOT / "backend" / ".env", debug=DEBUG_ENV)
load_env_file(ROOT / ".env", debug=DEBUG_ENV)

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")

if DEBUG_ENV:
    print(f"[DEBUG] ETHERSCAN_API_KEY loaded: {ETHERSCAN_API_KEY is not None}")
    if ETHERSCAN_API_KEY:
        print(f"[DEBUG] ETHERSCAN_API_KEY value (first 20 chars): {ETHERSCAN_API_KEY[:20]}")

# Example tokens
TOKENS = {
    "LINK": {
        "contract": "0x514910771af9ca656af840dff83e8264ecf986ca",
        "decimals": 18,
        "symbol": "LINK",
    },
    "USDC": {
        "contract": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        "decimals": 6,
        "symbol": "USDC",
    },
    "USDT": {
        "contract": "0xdac17f958d2ee523a2206206994597c13d831ec7",
        "decimals": 6,
        "symbol": "USDT",
    },
    "DAI": {
        "contract": "0x6b175474e89094c44da98b954eedeac495271d0f",
        "decimals": 18,
        "symbol": "DAI",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# API Functions
# ─────────────────────────────────────────────────────────────────────────────

def fetch_total_supply(contract: str) -> Optional[int]:
    """Fetch total supply from Etherscan."""
    params = {
        "chainid": "1",  # Ethereum mainnet
        "module": "proxy",
        "action": "eth_call",
        "to": contract,
        "data": "0x18160ddd",  # totalSupply() function selector
        "apikey": ETHERSCAN_API_KEY,
    }
    
    try:
        response = requests.get(ETHERSCAN_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        # V2 API returns result directly (no status field)
        hex_value = result.get("result")
        if hex_value and hex_value.startswith("0x"):
            try:
                supply = int(hex_value, 16)
                return supply
            except ValueError:
                print("  ⚠ Error parsing hex value:")
                print(f"     hex_value={hex_value}")
                return None
        else:
            print("  ⚠ Error fetching supply:")
            print(f"     status={result.get('status')}")
            print(f"     message={result.get('message', 'Unknown')}")
            print(f"     result={result.get('result')}")
            return None
    except Exception as e:
        print(f"  ❌ Exception fetching supply: {e}")
        return None


def fetch_token_holders(contract: str, page: int = 1, limit: int = 10000) -> Optional[list]:
    """Fetch top token holders from Etherscan V2 (tokentopholders action)."""
    params = {
        "chainid": "1",  # Ethereum mainnet
        "module": "token",
        "action": "tokentopholders",  # V2 endpoint for top holders
        "contractaddress": contract,
        "page": page,
        "offset": limit,
        "apikey": ETHERSCAN_API_KEY,
    }
    
    try:
        response = requests.get(ETHERSCAN_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if result.get("status") == "1":
            return result.get("result", [])
        else:
            # Rate limit or error
            message = result.get("message", "Unknown error")
            print("  ⚠ Error fetching holders:")
            print(f"     status={result.get('status')}")
            print(f"     message={message}")
            print(f"     full_result={result}")
            if "rate limit" in message.lower():
                print("  💡 Tip: Upgrade to a paid Etherscan plan or wait 1 second between requests.")
            return None
    except Exception as e:
        print(f"  ❌ Exception fetching holders: {e}")
        return None


def normalize_balance(balance_hex: str, decimals: int) -> float:
    """Convert hex balance to human-readable amount."""
    balance_int = int(balance_hex, 16)
    return balance_int / (10 ** decimals)


# ─────────────────────────────────────────────────────────────────────────────
# Analysis Functions
# ─────────────────────────────────────────────────────────────────────────────

def calculate_holder_metrics(holders: list, total_supply: int, decimals: int) -> dict:
    """Calculate concentration metrics from holder list."""
    if not holders or total_supply == 0:
        return {}
    
    # Extract balances
    balances = []
    for holder in holders:
        try:
            balance_int = int(holder.get("TokenHolderQuantity", 0))
            balances.append(balance_int)
        except (ValueError, TypeError):
            continue
    
    if not balances:
        return {}
    
    balances.sort(reverse=True)
    total = sum(balances)
    
    # Top holder percentages
    top_1_balance = balances[0] if len(balances) > 0 else 0
    top_10_sum = sum(balances[:10])
    top_100_sum = sum(balances[:100])
    
    top_1_pct = (top_1_balance / total * 100) if total > 0 else 0
    top_10_pct = (top_10_sum / total * 100) if total > 0 else 0
    top_100_pct = (top_100_sum / total * 100) if total > 0 else 0
    
    # Gini coefficient (simple approximation)
    n = len(balances)
    gini = (2 * sum((i + 1) * b for i, b in enumerate(balances))) / (n * total) - (n + 1) / n if total > 0 else 0
    
    # Herfindahl-Hirschman Index (HHI)
    hhi = sum((b / total) ** 2 for b in balances) if total > 0 else 0
    
    return {
        "holder_count": len(balances),
        "top_1_pct": round(top_1_pct, 2),
        "top_10_pct": round(top_10_pct, 2),
        "top_100_pct": round(top_100_pct, 2),
        "gini": round(gini, 4),
        "hhi": round(hhi, 4),
        "top_balances": [
            {
                "rank": i + 1,
                "address": balances[i] if i < len(holders) else "N/A",
                "balance": balances[i],
                "pct_of_total": round(balances[i] / total * 100, 2) if total > 0 else 0,
            }
            for i in range(min(10, len(balances)))
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 80)
    print("Etherscan Token Holder Diversity Fetcher")
    print("=" * 80)
    print()
    
    for token_name, token_info in TOKENS.items():
        print(f"\n📊 Fetching {token_name} ({token_info['symbol']})")
        print(f"   Contract: {token_info['contract']}")
        print("-" * 80)
        
        # Fetch total supply
        print("  ⏳ Fetching total supply...")
        total_supply = fetch_total_supply(token_info["contract"])
        if total_supply is None:
            print(f"  ❌ Could not fetch total supply. Skipping {token_name}.")
            continue
        
        print(f"  ✅ Total supply: {total_supply / (10 ** token_info['decimals']):,.0f}")
        
        # Rate limit: wait 1 second between API calls
        time.sleep(1)
        
        # Fetch holders
        print("  ⏳ Fetching top holders...")
        holders = fetch_token_holders(token_info["contract"], limit=10000)
        
        if holders is None or len(holders) == 0:
            print(f"  ❌ Could not fetch holders. Skipping {token_name}.")
            continue
        
        print(f"  ✅ Fetched {len(holders)} holders")
        
        # Calculate metrics
        print("  ⏳ Calculating metrics...")
        metrics = calculate_holder_metrics(holders, total_supply, token_info["decimals"])
        
        if metrics:
            print(f"  ✅ Metrics calculated")
            print()
            print("  📈 Summary:")
            print(f"     - Holder count: {metrics['holder_count']}")
            print(f"     - Top 1 holder: {metrics['top_1_pct']}%")
            print(f"     - Top 10 holders: {metrics['top_10_pct']}%")
            print(f"     - Top 100 holders: {metrics['top_100_pct']}%")
            print(f"     - Gini (0=equal, 1=one holder): {metrics['gini']}")
            print(f"     - HHI (concentration index): {metrics['hhi']}")
            print()
            print("  🏆 Top 10 holders:")
            for holder in metrics.get("top_balances", [])[:10]:
                print(f"     #{holder['rank']:2d} - {holder['pct_of_total']:6.2f}% of total")
        else:
            print(f"  ❌ Could not calculate metrics for {token_name}.")
        
        print()
    
    print("=" * 80)
    print("Done!")
    print("=" * 80)


if __name__ == "__main__":
    print("\n⚠️  IMPORTANT:")
    print("   Before running this script, you must:")
    print("   1. Create a free Etherscan account at https://etherscan.io/apis")
    print("   2. Copy your API key")
    print("   3. Put it into backend/.env as ETHERSCAN_API_KEY")
    print()

    if not ETHERSCAN_API_KEY:
        print("❌ API key not configured. Please add ETHERSCAN_API_KEY to backend/.env or .env and rerun.")
        exit(1)

    main()
