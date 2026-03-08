"""
Alias Updater Service
Populates and refreshes coin alias mappings in Redis cache.
"""

from typing import Dict, List, Optional
from services.apis.coingecko_list import CoinGeckoListProvider
from services.apis.coingecko_markets import CoinGeckoMarketsProvider
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
        self.markets_provider = CoinGeckoMarketsProvider()
        self.alias_ttl = 604800  # 7 days - aliases rarely change

    def _fetch_top_coin_symbols(self, top_n: int = 500) -> Dict[str, str]:
        """
        Fetch the top N coins by market cap and return a symbol -> id map.
        Used to resolve symbol collisions in favour of well-known coins.

        Args:
            top_n: How many top-market-cap coins to fetch (max 250 per page).

        Returns:
            Dict mapping lowercase symbol -> canonical coin id
        """
        symbol_map: Dict[str, str] = {}
        per_page = min(top_n, 250)
        pages = (top_n + per_page - 1) // per_page  # ceiling division

        for page in range(1, pages + 1):
            try:
                coins = self.markets_provider.fetch_top_coins(
                    per_page=per_page, page=page
                )
                for coin in coins:
                    coin_id = coin.get("id")
                    symbol = coin.get("symbol")
                    if coin_id and symbol:
                        # Only set if not already present – markets returns
                        # results in market_cap_desc order so first write wins
                        # (i.e. #1 coin's symbol beats #2's, etc.)
                        key = symbol.lower()
                        if key not in symbol_map:
                            symbol_map[key] = coin_id
            except Exception as e:
                print(f"[AliasUpdater] ✗ Failed to fetch top coins page {page}: {e}")
                break

        print(f"[AliasUpdater] ✓ Built priority symbol map for {len(symbol_map)} symbols")
        return symbol_map

    def update_all_aliases(self) -> Dict[str, any]:
        """
        Fetch coins list from CoinGecko and populate all alias mappings.
        
        For each coin, creates mappings:
        - id -> id (canonical)
        - symbol -> id  (top-market-cap coin wins on collision)
        - name -> id
        
        Returns:
            Dict with 'success', 'aliases_updated', 'coins_processed' keys
        """
        print("[AliasUpdater] Starting alias update...")
        
        # Fetch full coins list (id, symbol, name for every coin)
        coins = self.list_provider.fetch_coins_list()
        if not coins:
            return {
                "success": False,
                "error": "Failed to fetch coins list",
                "aliases_updated": 0,
                "coins_processed": 0
            }

        # Fetch top-500 coins by market cap to resolve symbol collisions.
        # e.g. both "bitcoin" and "batcat" have symbol "btc"; bitcoin should win
        # because it has a vastly higher market cap rank.
        priority_symbols = self._fetch_top_coin_symbols(top_n=500)

        # Build alias mappings dict for bulk insert
        aliases = {}
        for coin in coins:
            try:
                coin_id = coin.get("id")
                symbol = coin.get("symbol", "").lower()
                name = coin.get("name")
                
                if not coin_id:
                    continue
                
                # Map ID to itself (canonical) — always unique, no collision
                aliases[coin_id] = coin_id

                # Map symbol to ID.
                # Use the priority map so high-market-cap coins win collisions.
                # Fall back to first-come-first-served for unranked symbols.
                if symbol:
                    if symbol in priority_symbols:
                        aliases[symbol] = priority_symbols[symbol]
                    elif symbol not in aliases:
                        aliases[symbol] = coin_id
                
                # Map name to ID (first-come-first-served; names are mostly unique)
                if name and name not in aliases:
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
