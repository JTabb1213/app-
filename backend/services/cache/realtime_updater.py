"""
Real-time market data cache updater.
Fetches the top 50 coins from CoinGecko /coins/markets and stores them
in the standard tokenomics cache structure with a short TTL (2 minutes).

This bulk-updates the cache so the frontend gets live data without hitting
rate limits on the single-coin lookup endpoints.
"""

from typing import Dict, Any, List

from services.apis.coingecko_markets import coingecko_markets
from services.cache.service import cache_service
from config import CACHE_TTL_REALTIME


class RealtimeCacheUpdater:
    """
    Populates Redis with real-time market data for the top coins.
    Uses the standard tokenomics cache structure so the frontend reads
    it seamlessly via existing endpoints.
    """

    def __init__(self, markets_provider=None, cache=None):
        self.markets = markets_provider or coingecko_markets
        self.cache = cache or cache_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def update_top_coins(self, limit: int = 50) -> Dict[str, Any]:
        """
        Fetch top coins from CoinGecko and push real-time data into Redis cache.
        Uses Redis pipelining for efficient bulk updates.
        Stores in tokenomics format so frontend can read via /api/tokenomics/{id}.

        Args:
            limit: Number of top coins to fetch (default 50).

        Returns:
            Summary dict with counts and any errors.
        """
        try:
            raw_coins = self.markets.fetch_top_coins(per_page=limit)
        except Exception as e:
            return {"success": False, "error": str(e), "cached": 0}

        # Build tokenomics dict for bulk insert (much faster via pipelining)
        tokenomics_dict = {}
        errors: List[str] = []

        for coin in raw_coins:
            try:
                tokenomics_data = self._map_to_tokenomics(coin)
                coin_id = coin.get("id")
                tokenomics_dict[coin_id] = tokenomics_data
            except Exception as e:
                errors.append(f"{coin.get('id', '?')}: {e}")

        # Bulk cache using pipelining (single round-trip to Redis)
        cached = self.cache.set_bulk_tokenomics(tokenomics_dict, ttl=CACHE_TTL_REALTIME)

        summary = {
            "success": True,
            "cached": cached,
            "total_fetched": len(raw_coins),
            "errors": errors,
        }
        print(f"[RealtimeCache] ✓ Bulk cached {cached} coins in tokenomics cache (TTL {CACHE_TTL_REALTIME}s)")
        return summary

    # ------------------------------------------------------------------
    # Helper to map markets response to tokenomics structure
    # ------------------------------------------------------------------
    @staticmethod
    def _map_to_tokenomics(coin: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map CoinGecko /markets response to tokenomics structure.
        Matches the format expected by the frontend.
        """
        return {
            "name": coin.get("name"),
            "symbol": coin.get("symbol"),
            "current_price": coin.get("current_price"),
            "market_cap": coin.get("market_cap"),
            "total_volume": coin.get("total_volume"),  # 24h volume
            "price_change_percentage_24h": coin.get("price_change_percentage_24h"),
            "circulating_supply": coin.get("circulating_supply"),
            "total_supply": coin.get("total_supply"),
            "max_supply": coin.get("max_supply"),
        }


# Singleton
realtime_cache_updater = RealtimeCacheUpdater()
