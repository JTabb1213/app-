"""
Unified data service with automatic API fallback.
When one provider fails or is rate-limited, automatically tries the next.
Now includes Redis caching to reduce API calls and avoid rate limits.
"""

from typing import List, Optional, Dict, Any
from services.apis.base_provider import CryptoDataProvider
from services.apis.coingecko import CoinGeckoProvider
from services.cache import cache_service


class DataService:
    """
    Manages multiple crypto data providers with automatic fallback.
    Tries providers in order until one succeeds.
    Now cache-aware: checks Redis first, falls back to providers if cache miss.
    """
    
    def __init__(self, providers: Optional[List[CryptoDataProvider]] = None, 
                 use_cache: bool = True):
        """
        Initialize with a list of providers.
        
        Args:
            providers: List of provider instances. If None, uses default (CoinGecko only)
            use_cache: Whether to use Redis caching (default: True)
        """
        if providers is None:
            # Default to CoinGecko only for now
            self.providers = [CoinGeckoProvider()]
        else:
            self.providers = providers
        
        self.use_cache = use_cache
        self.cache = cache_service if use_cache else None
        self._last_successful_provider = None
    
    def get_coin_data(self, coin_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Fetch coin data, trying each provider until one succeeds.
        Note: coin_data is NOT cached (static metadata should go in SQL).
        
        Args:
            coin_id: Coin identifier (name, symbol, or ID)
            force_refresh: Included for API consistency (not used for coin_data)
            
        Returns:
            Comprehensive coin data dictionary
            
        Raises:
            Exception: If all providers fail
        """
        # Fetch from providers (no caching for static coin metadata)
        errors = []
        
        # Try last successful provider first (optimization)
        providers_to_try = self.providers.copy()
        if self._last_successful_provider and self._last_successful_provider in providers_to_try:
            providers_to_try.remove(self._last_successful_provider)
            providers_to_try.insert(0, self._last_successful_provider)
        
        for provider in providers_to_try:
            try:
                print(f"[DataService] Trying {provider.get_provider_name()}...")
                data = provider.get_coin_data(coin_id)
                self._last_successful_provider = provider
                print(f"[DataService] ✓ Success with {provider.get_provider_name()}")
                return data
            except Exception as e:
                error_msg = f"{provider.get_provider_name()}: {str(e)}"
                errors.append(error_msg)
                print(f"[DataService] ✗ {error_msg}")
                continue
        
        # All providers failed
        raise Exception(f"All providers failed. Errors: {'; '.join(errors)}")
    
    def get_tokenomics(self, coin_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Fetch tokenomics, trying each provider until one succeeds.
        Checks cache first if enabled (unless force_refresh=True).
        
        Args:
            coin_id: Coin identifier
            force_refresh: If True, bypass cache and fetch fresh data
            
        Returns:
            Tokenomics dictionary with market cap, supply, etc.
            
        Raises:
            Exception: If all providers fail
        """
        # Try cache first (unless force refresh)
        if self.use_cache and not force_refresh:
            cached_data = self.cache.get_tokenomics(coin_id)
            if cached_data:
                print(f"[DataService] ✓ Cache hit for tokenomics: {coin_id}")
                return cached_data
            print(f"[DataService] Cache miss for tokenomics: {coin_id}")
        elif force_refresh:
            print(f"[DataService] Force refresh for tokenomics: {coin_id}")
        
        # Cache miss or cache disabled - fetch from providers
        errors = []
        
        providers_to_try = self.providers.copy()
        if self._last_successful_provider and self._last_successful_provider in providers_to_try:
            providers_to_try.remove(self._last_successful_provider)
            providers_to_try.insert(0, self._last_successful_provider)
        
        for provider in providers_to_try:
            try:
                data = provider.get_tokenomics(coin_id)
                self._last_successful_provider = provider
                
                # Store in cache for future requests
                if self.use_cache:
                    self.cache.set_tokenomics(coin_id, data)
                
                return data
            except Exception as e:
                errors.append(f"{provider.get_provider_name()}: {str(e)}")
                continue
        
        raise Exception(f"All providers failed. Errors: {'; '.join(errors)}")
    
    def add_provider(self, provider: CryptoDataProvider):
        """Add a new provider to the fallback chain."""
        self.providers.append(provider)
    
    def remove_provider(self, provider: CryptoDataProvider):
        """Remove a provider from the fallback chain."""
        if provider in self.providers:
            self.providers.remove(provider)
    
    def check_provider_health(self) -> Dict[str, bool]:
        """Check health of all providers."""
        return {
            provider.get_provider_name(): provider.check_health()
            for provider in self.providers
        }


# Create singleton instance
data_service = DataService()
