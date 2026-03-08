"""
CoinGecko Markets API provider.
Fetches the top N coins by market cap from the /coins/markets endpoint.
"""

import requests
from typing import List, Dict, Any
from config import COINGECKO_BASE_URL


MARKETS_URL = f"{COINGECKO_BASE_URL}/coins/markets"


class CoinGeckoMarketsProvider:
    """
    Fetches top coins by market cap from CoinGecko's /coins/markets endpoint.
    Returns both static data (for DB storage) and real-time data (for cache).
    """

    def __init__(self, base_url: str = COINGECKO_BASE_URL):
        self.markets_url = f"{base_url}/coins/markets"

    def fetch_top_coins(
        self,
        vs_currency: str = "usd",
        per_page: int = 50,
        page: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Fetch top coins by market cap.

        Args:
            vs_currency: Quote currency (default "usd")
            per_page: Number of results per page (max 250)
            page: Page number

        Returns:
            Raw list of coin dicts from CoinGecko.

        Raises:
            Exception on HTTP or network errors.
        """
        params = {
            "vs_currency": vs_currency,
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": page,
            "sparkline": "false",
        }

        response = requests.get(self.markets_url, params=params, timeout=10)

        if response.status_code == 429:
            raise Exception("CoinGecko rate limit exceeded – try again shortly")
        if response.status_code != 200:
            raise Exception(
                f"CoinGecko /coins/markets returned status {response.status_code}"
            )

        data = response.json()
        if not isinstance(data, list):
            raise Exception("Unexpected response format from /coins/markets")

        print(f"[CoinGeckoMarkets] ✓ Fetched {len(data)} coins (page {page})")
        return data

    @staticmethod
    def extract_realtime_data(coin: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pull out the real-time / frequently-changing fields from a markets
        response item, suitable for caching.
        """
        return {
            "id": coin.get("id"),
            "symbol": coin.get("symbol"),
            "name": coin.get("name"),
            "image": coin.get("image"),
            "current_price": coin.get("current_price"),
            "market_cap": coin.get("market_cap"),
            "market_cap_rank": coin.get("market_cap_rank"),
            "total_volume": coin.get("total_volume"),
            "high_24h": coin.get("high_24h"),
            "low_24h": coin.get("low_24h"),
            "price_change_24h": coin.get("price_change_24h"),
            "price_change_percentage_24h": coin.get("price_change_percentage_24h"),
            "market_cap_change_24h": coin.get("market_cap_change_24h"),
            "market_cap_change_percentage_24h": coin.get("market_cap_change_percentage_24h"),
            "last_updated": coin.get("last_updated"),
        }


# Singleton
coingecko_markets = CoinGeckoMarketsProvider()
