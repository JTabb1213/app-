"""
Scoring service package - safety/quality scoring for cryptocurrencies.
Combines multiple factors into comprehensive safety scores.
"""

from .service import get_score

__all__ = ['get_score']
