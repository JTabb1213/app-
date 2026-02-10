"""
CoinGecko Coins List API Provider
Fetches the complete list of coins with id, symbol, and name mappings.
"""

import requests
from typing import List, Dict, Optional
from config import COINGECKO_COINS_LIST_URL


class CoinGeckoListProvider:
    """Provider for fetching CoinGecko's complete coins list."""
    
    def __init__(self):
        """
        Initialize the provider.
        """
        self.api_url = COINGECKO_COINS_LIST_URL
        self.timeout = 30
    
    def fetch_coins_list(self) -> Optional[List[Dict[str, str]]]:
        """
        Fetch the complete list of coins from CoinGecko.
        
        Returns:
            List of dicts with 'id', 'symbol', 'name' keys, or None on error
            Example: [{"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"}, ...]
        """
        try:
            print(f"[CoinGeckoListProvider] Fetching coins list from {self.api_url}")
            response = requests.get(self.api_url, timeout=self.timeout)
            response.raise_for_status()
            
            coins = response.json()
            print(f"[CoinGeckoListProvider] ✓ Retrieved {len(coins)} coins")
            return coins
            
        except requests.exceptions.Timeout:
            print(f"[CoinGeckoListProvider] ✗ Request timed out after {self.timeout}s")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[CoinGeckoListProvider] ✗ Request failed: {e}")
            return None
        except Exception as e:
            print(f"[CoinGeckoListProvider] ✗ Unexpected error: {e}")
            return None
