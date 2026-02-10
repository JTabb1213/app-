"""
Cache updater service - responsible for triggering fresh data fetches
and populating the Redis cache.

This service is designed to be separable from the main API backend.
In production, this can run as:
- A separate microservice
- A scheduled background job (cron, Celery, etc.)
- An on-demand updater triggered via API

The main backend (data_service) handles both reads and writes to cache.
This service just triggers force-refresh operations through data_service.
"""

from typing import List


class CacheUpdaterService:
    """
    Triggers data_service to fetch fresh data and update cache.
    Designed to run independently from the main request-response cycle.
    """
    
    def __init__(self):
        """
        Initialize the cache updater.
        Note: We import data_service inside methods to avoid circular imports.
        """
        pass
    
    def update_coin(self, coin_id: str) -> dict:
        """
        Update cache for a specific coin by fetching fresh tokenomics via data_service.
        Note: Only tokenomics is cached. Coin metadata should be stored in SQL.
        
        Args:
            coin_id: Coin identifier (name, symbol, or ID)
            
        Returns:
            Status dictionary with success/failure info
        """
        # Import here to avoid circular dependency
        from services.data import data_service
        
        result = {
            "coin_id": coin_id,
            "tokenomics_updated": False,
            "errors": []
        }
        
        try:
            print(f"[CacheUpdater] Updating tokenomics for {coin_id} via data_service...")
            
            try:
                data_service.get_tokenomics(coin_id, force_refresh=True)
                result["tokenomics_updated"] = True
                print(f"[CacheUpdater] ✓ Successfully updated cache for {coin_id}")
            except Exception as e:
                result["errors"].append(str(e))
                print(f"[CacheUpdater] ✗ Failed to update {coin_id}: {e}")
                
        except Exception as e:
            result["errors"].append(str(e))
            print(f"[CacheUpdater] ✗ Error updating {coin_id}: {e}")
        
        return result
    
    def update_multiple_coins(self, coin_ids: List[str]) -> dict:
        """
        Update cache for multiple coins (tokenomics only).
        Useful for batch updates or scheduled refreshes.
        
        Args:
            coin_ids: List of coin identifiers
            
        Returns:
            Summary dictionary with success/failure counts
        """
        results = []
        success_count = 0
        failure_count = 0
        
        print(f"[CacheUpdater] Starting batch update for {len(coin_ids)} coins...")
        
        for coin_id in coin_ids:
            result = self.update_coin(coin_id)
            results.append(result)
            
            if result["tokenomics_updated"]:
                success_count += 1
            else:
                failure_count += 1
        
        summary = {
            "total": len(coin_ids),
            "succeeded": success_count,
            "failed": failure_count,
            "results": results
        }
        
        print(f"[CacheUpdater] ✓ Batch update complete: {success_count} succeeded, {failure_count} failed")
        return summary
    
    def update_popular_coins(self, limit: int = 20) -> dict:
        """
        Update cache for the most popular coins.
        Useful for proactively warming the cache with commonly-requested data.
        
        Args:
            limit: Number of top coins to update
            
        Returns:
            Summary of update results
        """
        # List of popular coins to keep warm in cache
        popular_coins = [
            "bitcoin", "ethereum", "tether", "binancecoin", "solana",
            "usd-coin", "ripple", "cardano", "avalanche-2", "dogecoin",
            "polkadot", "tron", "chainlink", "polygon", "litecoin",
            "near", "uniswap", "internet-computer", "cosmos", "stellar"
        ]
        
        coins_to_update = popular_coins[:limit]
        return self.update_multiple_coins(coins_to_update)
    
    def get_cache_stats(self) -> dict:
        """
        Get current cache statistics.
        Useful for monitoring cache health and usage.
        
        Returns:
            Cache statistics dictionary
        """
        from services.cache.service import cache_service
        return cache_service.get_stats()


# Create singleton instance
cache_updater = CacheUpdaterService()
