import requests
from config import COINGECKO_BASE_URL
from .base_provider import CryptoDataProvider


class CoinGeckoProvider(CryptoDataProvider):
    """CoinGecko API implementation."""
    
    def __init__(self):
        self.base_url = COINGECKO_BASE_URL
        self._coin_id_cache = {}
    
    def get_provider_name(self) -> str:
        return "CoinGecko"
    
    def check_health(self) -> bool:
        """Check if CoinGecko API is accessible."""
        try:
            response = requests.get(f"{self.base_url}/ping", timeout=3)
            return response.status_code == 200
        except:
            return False
    
    def resolve_coin_id(self, search_query: str) -> str:
        """
        Dynamically resolve a coin search query to a CoinGecko coin ID.
        First tries the query as-is, then uses search API if needed.
        Caches results to avoid repeated API calls.
        """
        query_lower = search_query.lower().strip()
        
        # Check cache first
        if query_lower in self._coin_id_cache:
            return self._coin_id_cache[query_lower]
        
        # Try the query as-is
        try:
            response = requests.get(f"{self.base_url}/coins/{query_lower}", timeout=5)
            if response.status_code == 200:
                coin_id = response.json().get("id", query_lower)
                self._coin_id_cache[query_lower] = coin_id
                return coin_id
            elif response.status_code == 429:
                print(f"[RATE LIMIT] 429 from CoinGecko /coins endpoint for query: {query_lower}")
            else:
                print(f"[CoinGecko] Non-200 status {response.status_code} from /coins/{query_lower}")
        except Exception as e:
            print(f"[CoinGecko] Exception in direct lookup: {e}")
        
        # If direct lookup fails, use search API
        try:
            response = requests.get(
                f"{self.base_url}/search",
                params={"query": query_lower},
                timeout=5
            )
            
            if response.status_code == 200:
                coins = response.json().get("coins", [])
                if coins:
                    # Return the first (most relevant) result
                    coin_id = coins[0].get("id")
                    self._coin_id_cache[query_lower] = coin_id
                    return coin_id
            elif response.status_code == 429:
                print(f"[RATE LIMIT] 429 from CoinGecko /search endpoint for query: {query_lower}")
            else:
                print(f"[CoinGecko] Non-200 status {response.status_code} from /search?query={query_lower}")
        except Exception as e:
            print(f"[CoinGecko] Exception in search: {e}")
        
        # If all else fails, raise an error
        raise Exception(f"Coin '{search_query}' not found")
    
    def get_coin_data(self, coin_id: str):
        """Fetch comprehensive coin data."""
        # Dynamically resolve the coin ID
        resolved_coin_id = self.resolve_coin_id(coin_id)
        
        response = requests.get(f"{self.base_url}/coins/{resolved_coin_id}")
        
        if response.status_code == 429:
            print(f"[RATE LIMIT] 429 from CoinGecko /coins/{resolved_coin_id} endpoint")
            raise Exception("CoinGecko rate limit exceeded - please try again in a moment")
        elif response.status_code != 200:
            print(f"[CoinGecko] Error {response.status_code} fetching coin data for {resolved_coin_id}")
            raise Exception("Coin not found")

        return response.json()
    
    def get_tokenomics(self, coin_id: str):
        """Fetch tokenomics data."""
        data = self.get_coin_data(coin_id)

        tokenomics = {
            "name": data["name"],
            "symbol": data["symbol"],
            "market_cap": data["market_data"]["market_cap"]["usd"],
            "circulating_supply": data["market_data"]["circulating_supply"],
            "total_supply": data["market_data"]["total_supply"],
            "max_supply": data["market_data"]["max_supply"],
        }

        return tokenomics


# Create a singleton instance for backward compatibility
#_provider = CoinGeckoProvider()

# Export legacy function names for existing code. Only used by code that hasn't
# yet migrated to DataService. Can be removed once all code uses DataService.
# Note: legacy module-level singleton and wrapper functions removed.
# Use the unified `data_service` (services.data_service.data_service) or
# instantiate `CoinGeckoProvider` directly when needed.
