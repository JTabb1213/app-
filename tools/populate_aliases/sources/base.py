"""
Abstract base class for alias data sources.

To add a new exchange:
  1. Create tools/populate_aliases/sources/<exchange>.py
  2. Subclass BaseAliasSource
  3. Implement enrich(assets) — add exchange_symbols and any extra aliases
  4. Register it in tools/populate_aliases/main.py

The separation between CoinGeckoSource (builds the canonical asset list) and
exchange sources (enrich() only adds exchange_symbols to existing entries) is
intentional: CoinGecko is the canonical ID authority; exchanges just tell us
what names they use for the same assets.
"""

from abc import ABC, abstractmethod
from typing import Dict


# Type alias for the shared assets dict passed between sources
# Structure: { canonical_id: { "symbol": str, "coingecko_id": str,
#                               "aliases": [str], "exchange_symbols": {str: str} } }
AssetsDict = Dict[str, dict]


class BaseAliasSource(ABC):
    """Base class for all alias data sources."""

    # Subclasses set this so the CLI can reference them by name
    SOURCE_NAME: str = ""

    @abstractmethod
    def enrich(self, assets: AssetsDict) -> None:
        """
        Mutate the shared assets dict in-place.

        For CoinGecko (the primary source) this *creates* entries.
        For exchange sources this *adds* exchange_symbols to existing entries
        and optionally appends exchange-specific strings to the aliases list.

        Args:
            assets: Shared assets dict — modified in place.
        """
        raise NotImplementedError
