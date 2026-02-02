"""
Abstract base class for cryptocurrency data providers.
All API providers should inherit from this and implement the required methods.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class CryptoDataProvider(ABC):
    """Base class for crypto data API providers."""
    
    @abstractmethod
    def get_coin_data(self, coin_id: str) -> Dict[str, Any]:
        """
        Fetch comprehensive coin data including market data and links.
        
        Args:
            coin_id: The coin identifier (can be name, symbol, or provider-specific ID)
            
        Returns:
            Dictionary with standardized coin data
            
        Raises:
            Exception: If coin not found or API error
        """
        pass
    
    @abstractmethod
    def get_tokenomics(self, coin_id: str) -> Dict[str, Any]:
        """
        Fetch tokenomics data for a coin.
        
        Args:
            coin_id: The coin identifier
            
        Returns:
            Dictionary with: name, symbol, market_cap, circulating_supply, 
            total_supply, max_supply
            
        Raises:
            Exception: If coin not found or API error
        """
        pass
    
    @abstractmethod
    def resolve_coin_id(self, query: str) -> Optional[str]:
        """
        Resolve a search query to a provider-specific coin ID.
        
        Args:
            query: Search string (e.g., "bitcoin", "btc", "ethereum")
            
        Returns:
            Provider-specific coin ID, or None if not found
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of this provider (e.g., 'CoinGecko', 'CoinMarketCap')"""
        pass
    
    @abstractmethod
    def check_health(self) -> bool:
        """
        Check if the API is accessible and not rate-limited.
        
        Returns:
            True if API is healthy, False otherwise
        """
        pass
