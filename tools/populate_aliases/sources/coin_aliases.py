"""
Coin alias source.

Enriches the assets dict with manually curated aliases for each coin.
Reads from sources/coin_aliases/coin_aliases.json — a hand-maintained
file where you list every string you want the resolver to recognise for
a given coin.

Why manual instead of auto-derived?
  CoinGecko gives us [canonical_id, symbol, display_name] automatically,
  which covers most cases.  But common human shortcuts aren't captured:
    "avalanche-2" is the canonical ID but no user types it that way
    "ether" is commonly used for ethereum but isn't the display name
    "synthetix" is used more than its canonical ID "havven"
  This file is your escape hatch to add anything the auto-derivation misses.

If a coin has NO entry here, it falls back to auto-derived aliases:
    [canonical_id, symbol.lower(), display_name.lower()]
which coingecko.py already sets when building the base asset list.

Adding aliases:
  1. Find the coin's CoinGecko canonical ID (e.g. "avalanche-2")
  2. Add it to sources/coin_aliases/coin_aliases.json
  3. Re-run:  python main.py

Adding more exchanges later:
  Exchange aliases live in exchange_symbols/<exchange>_symbols.json
  and are handled by their own source files (see kraken.py as the template).
"""

import json
import os
from typing import Dict, List, Optional

from .base import BaseAliasSource, AssetsDict

_ALIASES_FILE = os.path.join(
    os.path.dirname(__file__), "coin_aliases", "coin_aliases.json"
)


class CoinAliasSource(BaseAliasSource):
    """
    Enriches assets with manually curated alias lists.

    For each coin that has a curated entry in coin_aliases.json, the
    auto-derived aliases from CoinGeckoSource are replaced with the
    curated list.  Coins with no entry keep the auto-derived aliases.
    """

    SOURCE_NAME = "coin_aliases"

    # ------------------------------------------------------------------
    # BaseAliasSource interface
    # ------------------------------------------------------------------

    def enrich(self, assets: AssetsDict) -> None:
        mapping = self._load_mapping()
        if not mapping:
            print("[CoinAliasSource] ✗ No alias mapping loaded — skipping.")
            return

        enriched = 0
        unmatched = 0   # curated entries whose coin isn't in the current top-N

        for canonical_id, aliases in mapping.items():
            if canonical_id not in assets:
                unmatched += 1
                continue
            assets[canonical_id]["aliases"] = aliases
            enriched += 1

        auto = len(assets) - enriched
        print(
            f"[CoinAliasSource] ✓ Applied curated aliases to {enriched} assets"
        )
        if auto:
            print(
                f"[CoinAliasSource]   {auto} assets using auto-derived aliases "
                f"(not in coin_aliases.json)"
            )
        if unmatched:
            print(
                f"[CoinAliasSource]   {unmatched} curated entries skipped "
                f"(not in current CoinGecko top-N)"
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_mapping(self) -> Optional[Dict[str, List[str]]]:
        """Load the curated coin_aliases.json mapping file."""
        try:
            with open(_ALIASES_FILE, "r") as f:
                data = json.load(f)
            mapping = data.get("aliases", {})
            print(
                f"[CoinAliasSource]   Loaded {len(mapping)} curated "
                f"entries from coin_aliases.json"
            )
            return mapping
        except FileNotFoundError:
            print(f"[CoinAliasSource] ✗ Aliases file not found: {_ALIASES_FILE}")
            return None
        except json.JSONDecodeError as e:
            print(f"[CoinAliasSource] ✗ Invalid JSON in aliases file: {e}")
            return None
