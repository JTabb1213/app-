"""
Redis cache service for storing cryptocurrency data.
Provides a clean interface for cache operations (get, set, delete).
Only caches frequently-changing tokenomics data.
Static coin metadata should be stored in SQL database.
"""

import json
import redis
from typing import Optional, Dict, Any
from config import REDIS_URL, CACHE_TTL_TOKENOMICS
from services.alias.resolver import alias_resolver


class CacheService:
    """
    Redis cache service for cryptocurrency data.
    Handles serialization, key generation, and TTL management.
    """
    
    def __init__(self, redis_url: str = REDIS_URL):
        """
        Initialize Redis connection.
        
        Args:
            redis_url: Redis connection URL (use rediss:// for TLS)
        """
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self._check_connection()
    
    def _check_connection(self):
        """Verify Redis connection on startup."""
        try:
            self.redis_client.ping()
            print("[CacheService] ✓ Connected to Redis")
        except Exception as e:
            print(f"[CacheService] ✗ Redis connection failed: {e}")
            raise
    
    def _make_key(self, data_type: str, coin_id: str) -> str:
        """
        Generate a cache key, resolving aliases to canonical coin ID.

        Uses the in-memory alias resolver (backed by data/coin_aliases.json)
        instead of Redis — ~200× faster and works on first boot with no
        pre-seeding required.

        Args:
            data_type: Type of data ('tokenomics', etc.)
            coin_id: Coin identifier (will be resolved via alias map)

        Returns:
            Cache key string with canonical coin ID
        """
        canonical_id = alias_resolver.resolve(coin_id) or coin_id.lower()
        return f"crypto:{data_type}:{canonical_id}"
    
    def get_tokenomics(self, coin_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve tokenomics data from cache.
        
        Args:
            coin_id: Coin identifier
            
        Returns:
            Tokenomics dictionary or None if not in cache
        """
        key = self._make_key("tokenomics", coin_id)
        try:
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"[CacheService] Error reading tokenomics for {coin_id}: {e}")
            return None
    
    def set_tokenomics(self, coin_id: str, data: Dict[str, Any], ttl: int = CACHE_TTL_TOKENOMICS):
        """
        Store tokenomics data in cache.
        
        Args:
            coin_id: Coin identifier
            data: Tokenomics data dictionary
            ttl: Time to live in seconds
        """
        key = self._make_key("tokenomics", coin_id)
        try:
            self.redis_client.setex(key, ttl, json.dumps(data))
            print(f"[CacheService] ✓ Cached tokenomics for {coin_id} (TTL: {ttl}s)")
        except Exception as e:
            print(f"[CacheService] ✗ Error caching tokenomics for {coin_id}: {e}")
    
    def set_bulk_tokenomics(self, tokenomics_dict: Dict[str, Dict[str, Any]], ttl: int = CACHE_TTL_TOKENOMICS) -> int:
        """
        Efficiently store multiple tokenomics entries using Redis pipelining.
        
        Args:
            tokenomics_dict: Dict mapping coin_id -> tokenomics data
            ttl: Time to live in seconds
        
        Returns:
            Number of entries successfully cached
        """
        if not tokenomics_dict:
            return 0
        
        try:
            pipe = self.redis_client.pipeline(transaction=False)
            
            for coin_id, data in tokenomics_dict.items():
                key = self._make_key("tokenomics", coin_id)
                pipe.setex(key, ttl, json.dumps(data))
            
            pipe.execute()
            print(f"[CacheService] ✓ Bulk cached {len(tokenomics_dict)} tokenomics entries (TTL: {ttl}s)")
            return len(tokenomics_dict)
        except Exception as e:
            print(f"[CacheService] ✗ Error in bulk tokenomics cache: {e}")
            return 0
    
    def get_alias(self, search_term: str) -> Optional[str]:
        """
        Resolve a search term to its canonical coin ID.

        Delegates to the in-memory AliasResolver backed by
        data/coin_aliases.json.  Redis is no longer used for alias storage.

        Args:
            search_term: Coin name, symbol, or ID to resolve

        Returns:
            Canonical coin ID or None if not found
        """
        return alias_resolver.resolve(search_term)
    
    def delete(self, data_type: str, coin_id: str):
        """
        Delete a specific cache entry.
        
        Args:
            data_type: Type of data to delete
            coin_id: Coin identifier
        """
        key = self._make_key(data_type, coin_id)
        try:
            self.redis_client.delete(key)
            print(f"[CacheService] ✓ Deleted {data_type} for {coin_id}")
        except Exception as e:
            print(f"[CacheService] ✗ Error deleting {data_type} for {coin_id}: {e}")
    
    def flush_all(self):
        """
        Clear all cache entries.
        USE WITH CAUTION - deletes all data in Redis.
        """
        try:
            self.redis_client.flushdb()
            print("[CacheService] ✓ Flushed all cache")
        except Exception as e:
            print(f"[CacheService] ✗ Error flushing cache: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats (key count, memory usage, etc.)
        """
        try:
            info = self.redis_client.info()
            return {
                "connected": True,
                "total_keys": self.redis_client.dbsize(),
                "used_memory_human": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0)
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }


# Create singleton instance
cache_service = CacheService()
