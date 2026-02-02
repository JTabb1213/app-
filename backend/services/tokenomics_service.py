"""
Tokenomics service - fetches token supply and market data.
Uses unified data service with automatic API fallback.
"""

from services.data_service import data_service


def get_tokenomics(coin_id: str):
    """
    Get tokenomics data for a coin.
    Automatically tries multiple providers if one fails.
    """
    return data_service.get_tokenomics(coin_id)
