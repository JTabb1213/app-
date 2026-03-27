"""
Kraken alias source.

Enriches the shared assets dict with Kraken-specific exchange symbols
using a curated mapping file (exchange_symbols/kraken_symbols.json) instead of trying
to auto-match symbols to CoinGecko IDs.

Why curated instead of automated?
  Many Kraken symbols (SOL, DOT, ETH, etc.) collide with dozens of
  obscure CoinGecko coins that share the same ticker.  Automated
  matching picks the wrong coin more often than not at scale.
  A curated JSON file is explicit, version-controlled, and correct.

Adding new Kraken symbols:
  1. Run:  python main.py --sources kraken --print-assets
  2. Find new symbols not yet in exchange_symbols/kraken_symbols.json
  3. Look up the correct CoinGecko canonical ID
  4. Add the mapping to sources/exchange_symbols/kraken_symbols.json

Adding more exchanges later:
  Copy this pattern:
    sources/exchange_symbols/<exchange>_symbols.json   ← curated symbol mapping
    sources/<exchange>.py                              ← source class
"""

import json
import os
import requests
from typing import Dict, Optional

from .base import BaseAliasSource, AssetsDict

_KRAKEN_ASSETS_URL = "https://api.kraken.com/0/public/Assets"
_SYMBOLS_FILE = os.path.join(os.path.dirname(__file__), "exchange_symbols", "kraken_symbols.json")

# Kraken fiat currencies to skip when printing assets
_FIAT_ALTNAMES = {"USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "ARS", "COP", "DKK", "MXN", "PLN", "SEK", "FEE"}

# Staking/hold/margin suffixes to skip when printing
_SKIP_SUFFIXES = (".S", ".P", ".M", ".HOLD", "21.S", "28.S", "14.S", "07.S", "03.S", "04.S")


class KrakenSource(BaseAliasSource):
    """
    Enriches assets dict with Kraken exchange symbols from a curated
    mapping file (exchange_symbols/kraken_symbols.json).

    For each Kraken symbol that maps to an existing canonical ID in the
    assets dict, sets exchange_symbols["kraken"] = <symbol>.
    """

    SOURCE_NAME = "kraken"

    def __init__(self, print_assets: bool = False):
        self._print_assets = print_assets

    # ------------------------------------------------------------------
    # BaseAliasSource interface
    # ------------------------------------------------------------------

    def enrich(self, assets: AssetsDict) -> None:
        """
        Add Kraken exchange symbols to matching entries in the assets dict.

        Reads from exchange_symbols/kraken_symbols.json (curated mapping), NOT from auto-
        matching against CoinGecko symbols.  Only adds to coins that
        already exist in the assets dict (created by CoinGeckoSource).
        """
        # Optionally print raw Kraken assets to screen
        if self._print_assets:
            self._print_kraken_assets()

        # Load curated mapping
        mapping = self._load_symbol_mapping()
        if not mapping:
            print("[KrakenSource] ✗ No symbol mapping loaded — skipping.")
            return

        enriched = 0
        skipped_null = 0
        skipped_missing = []

        for kraken_sym, canonical_id in mapping.items():
            # null entries = intentionally unmapped (fiat, staking, etc.)
            if canonical_id is None:
                skipped_null += 1
                continue

            if canonical_id not in assets:
                skipped_missing.append(f"{kraken_sym}->{canonical_id}")
                continue

            assets[canonical_id]["exchange_symbols"]["kraken"] = kraken_sym
            enriched += 1

        print(f"[KrakenSource] ✓ Enriched {enriched} assets with Kraken symbols")
        print(f"[KrakenSource]   Skipped (null/unmapped): {skipped_null}")
        if skipped_missing:
            print(f"[KrakenSource]   Skipped (not in CoinGecko top-N): {len(skipped_missing)}")
            # Only show first 10 to avoid spam
            if len(skipped_missing) <= 10:
                print(f"[KrakenSource]   → {skipped_missing}")
            else:
                print(f"[KrakenSource]   → {skipped_missing[:10]} ... and {len(skipped_missing)-10} more")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_symbol_mapping(self) -> Optional[Dict[str, Optional[str]]]:
        """Load the curated exchange_symbols/kraken_symbols.json mapping file."""
        try:
            with open(_SYMBOLS_FILE, "r") as f:
                data = json.load(f)
            mapping = data.get("symbols", {})
            print(f"[KrakenSource]   Loaded {len(mapping)} symbol mappings from exchange_symbols/kraken_symbols.json")
            return mapping
        except FileNotFoundError:
            print(f"[KrakenSource] ✗ Mapping file not found: {_SYMBOLS_FILE}")
            print("[KrakenSource]   Create it with curated Kraken→CoinGecko mappings in exchange_symbols/.")
            return None
        except json.JSONDecodeError as e:
            print(f"[KrakenSource] ✗ Invalid JSON in mapping file: {e}")
            return None

    def _print_kraken_assets(self) -> None:
        """Fetch and print all Kraken asset altnames to screen."""
        raw = self._fetch_assets()
        if not raw:
            print("[KrakenSource] ✗ Could not fetch Kraken assets for printing.")
            return

        # Get all altnames, skip fiat and staking variants
        altnames = sorted(set(
            a.get("altname", "") for a in raw.values()
            if a.get("altname", "")
            and a.get("altname", "") not in _FIAT_ALTNAMES
            and not any(a.get("altname", "").endswith(s) for s in _SKIP_SUFFIXES)
        ))

        # Load existing mapping to show what's mapped vs unmapped
        mapping = self._load_symbol_mapping() or {}

        mapped = [a for a in altnames if a in mapping and mapping[a] is not None]
        unmapped = [a for a in altnames if a not in mapping]
        null_mapped = [a for a in altnames if a in mapping and mapping[a] is None]

        print(f"\n{'='*60}")
        print(f"  KRAKEN ASSETS ({len(altnames)} crypto symbols)")
        print(f"{'='*60}")
        print(f"  Mapped:   {len(mapped)}")
        print(f"  Unmapped: {len(unmapped)}  ← add these to exchange_symbols/kraken_symbols.json")
        print(f"  Null:     {len(null_mapped)}  (intentionally skipped)")

        if unmapped:
            print(f"\n  --- UNMAPPED (need CoinGecko IDs) ---")
            for sym in unmapped:
                print(f"    {sym}")

        print(f"\n  --- ALL SYMBOLS ---")
        for sym in altnames:
            status = "✓" if sym in mapping and mapping[sym] else ("–" if sym in mapping else "?")
            cg_id = mapping.get(sym, "")
            print(f"    {status} {sym:20s} → {cg_id or '(unmapped)'}")

        print(f"{'='*60}\n")

    def _fetch_assets(self) -> Optional[Dict]:
        """Call Kraken's public /Assets endpoint and return the result dict."""
        try:
            resp = requests.get(_KRAKEN_ASSETS_URL, timeout=15)
            resp.raise_for_status()
            payload = resp.json()

            errors = payload.get("error", [])
            if errors:
                print(f"[KrakenSource] ✗ Kraken API error: {errors}")
                return None

            result = payload.get("result", {})
            print(f"[KrakenSource]   Fetched {len(result)} Kraken assets from API")
            return result

        except requests.exceptions.RequestException as e:
            print(f"[KrakenSource] ✗ Request failed: {e}")
            return None
            return None
