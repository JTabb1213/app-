"""
Abstract base class for alias data sources.

To add a new exchange:
  1. Create tools/populate_aliases/sources/<exchange>_symbols.json
     with curated { "symbols": { "EXCHANGE_SYM": "canonical_id", ... } }
  2. Create tools/populate_aliases/sources/<exchange>.py
  3. Subclass BaseAliasSource and implement enrich()
  4. Register it in tools/populate_aliases/main.py

The separation between CoinGeckoSource (builds the canonical asset list) and
exchange sources (enrich() only adds exchange mappings to existing entries) is
intentional: CoinGecko is the canonical ID authority; exchanges just tell us
what names they use for the same assets.
"""

from abc import ABC, abstractmethod
from typing import Dict


# Type alias for the shared assets dict passed between sources.
#
# Schema:
# {
#     canonical_id: {
#         "symbol":          "BTC",         # Standard ticker (uppercase)
#         "aliases":         ["bitcoin",    # All searchable terms (lowercase)
#                             "btc",
#                             "xbt"],
#         "exchange_symbols": {              # Exchange-specific symbols (curated)
#             "kraken": "XBT",
#         }
#     }
# }
#
# Source pipeline (run in order):
#   1. coingecko     — builds the canonical asset list + auto-derived aliases
#   2. coin_aliases  — replaces aliases with manually curated lists where available
#   3. kraken        — adds exchange_symbols["kraken"] from exchange_symbols/kraken_symbols.json
#   (future)         — add more exchange sources following the kraken.py pattern
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
        For exchange sources this *adds* exchange mappings to existing entries.

        Args:
            assets: Shared assets dict — modified in place.
        """
        raise NotImplementedError
