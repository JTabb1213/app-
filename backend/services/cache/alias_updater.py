"""
Alias Updater Service
Populates and refreshes coin alias mappings in Redis cache.
"""

from typing import Dict, List, Optional
from services.apis.coingecko_list import CoinGeckoListProvider
from services.cache.service import CacheService


class AliasUpdater:
    """Manages alias updates from CoinGecko's coins list."""
    
    def __init__(self, cache_service: CacheService):
        """
        Initialize the alias updater.
        
        Args:
            cache_service: Redis cache service instance
        """
        self.cache_service = cache_service
        self.list_provider = CoinGeckoListProvider()
        self.alias_ttl = 604800  # 7 days - aliases rarely change
    
    def update_all_aliases(self) -> Dict[str, any]:
        """
        Fetch coins list from CoinGecko and populate all alias mappings.
        
        For each coin, creates mappings:
        - id -> id (canonical)
        - symbol -> id
        - name -> id
        
        Returns:
            Dict with 'success', 'aliases_updated', 'coins_processed' keys
        """
        print("[AliasUpdater] Starting alias update...")
        
        # Fetch coins list
        coins = self.list_provider.fetch_coins_list()
        if not coins:
            return {
                "success": False,
                "error": "Failed to fetch coins list",
                "aliases_updated": 0,
                "coins_processed": 0
            }
        
        # Build alias mappings dict for bulk insert
        aliases = {}
        for coin in coins:
            try:
                coin_id = coin.get("id")
                symbol = coin.get("symbol")
                name = coin.get("name")
                
                if not coin_id:
                    continue
                
                # Map ID to itself (canonical)
                aliases[coin_id] = coin_id
                
                # Map symbol to ID
                if symbol:
                    aliases[symbol] = coin_id
                
                # Map name to ID
                if name:
                    aliases[name] = coin_id
                    
            except Exception as e:
                print(f"[AliasUpdater] Error processing coin {coin}: {e}")
                continue
        
        # Bulk insert all aliases using pipeline
        aliases_updated = self.cache_service.set_bulk_aliases(aliases, self.alias_ttl)
        
        print(f"[AliasUpdater] ✓ Updated {aliases_updated} aliases from {len(coins)} coins")
        return {
            "success": True,
            "aliases_updated": aliases_updated,
            "coins_processed": len(coins)
        }
    
    def update_single_coin(self, coin_id: str, symbol: str, name: str) -> bool:
        """
        Update aliases for a single coin.
        
        Args:
            coin_id: Canonical coin ID
            symbol: Coin symbol
            name: Coin name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.cache_service.set_alias(coin_id, coin_id, self.alias_ttl)
            if symbol:
                self.cache_service.set_alias(symbol, coin_id, self.alias_ttl)
            if name:
                self.cache_service.set_alias(name, coin_id, self.alias_ttl)
            return True
        except Exception as e:
            print(f"[AliasUpdater] Error updating aliases for {coin_id}: {e}")
            return False
