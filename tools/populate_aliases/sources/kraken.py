"""
Kraken alias source.

Enriches the shared assets dict with Kraken-specific exchange symbols by
calling Kraken's public /Assets endpoint.  No API key required.

Why this matters:
  Kraken uses 'XBT' for bitcoin (ISO 4217 convention) instead of 'BTC'.
  Without this mapping, parsing a Kraken WebSocket feed for "XBT/USD"
  would fail to resolve to the canonical ID "bitcoin".

Adding more exchanges later:
  Copy this file as tools/populate_aliases/sources/<exchange>.py,
  subclass BaseAliasSource, implement enrich(), then register it in main.py.
"""

import requests
from typing import Dict, Optional

from .base import BaseAliasSource, AssetsDict

_KRAKEN_ASSETS_URL = "https://api.kraken.com/0/public/Assets"

# Hardcoded overrides for cases where Kraken's altname doesn't match the
# standard symbol used in the CoinGecko-built assets dict.
# Key   = Kraken altname  (what Kraken calls it)
# Value = canonical_id    (CoinGecko convention)
#
# Add new entries here whenever you discover a Kraken/CoinGecko mismatch.
KNOWN_OVERRIDES: Dict[str, str] = {
    "XBT": "bitcoin",    # Kraken: XBT  ↔  CoinGecko: bitcoin (symbol BTC)
    "XDG": "dogecoin",   # Kraken: XDG  ↔  CoinGecko: dogecoin (symbol DOGE)
}

# Kraken internal asset codes use these prefixes for "real" currencies.
# We skip assets that are clearly fiat (start with Z) but keep stablecoins.
_FIAT_ALTNAMES = {"USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF"}


class KrakenSource(BaseAliasSource):
    """
    Enriches assets dict with Kraken exchange symbols.

    For each Kraken asset whose altname maps to a known canonical ID:
      - Sets exchange_symbols["kraken"] = <altname>
      - Appends the lowercased altname to the aliases list (so the resolver
        can map incoming Kraken WebSocket data with no extra logic)
    """

    SOURCE_NAME = "kraken"

    # ------------------------------------------------------------------
    # BaseAliasSource interface
    # ------------------------------------------------------------------

    def enrich(self, assets: AssetsDict) -> None:
        """
        Add Kraken exchange symbols to matching entries in the assets dict.

        Does NOT create new canonical entries — the CoinGeckoSource is the
        authority for what assets exist.  This only annotates existing ones.
        """
        raw = self._fetch_assets()
        if not raw:
            print("[KrakenSource] ✗ No data from Kraken — skipping enrichment.")
            return

        # Build a quick symbol → canonical_id lookup from the assets already
        # in the dict so we can match standard symbols without KNOWN_OVERRIDES.
        # e.g. {"eth": "ethereum", "sol": "solana", ...}
        symbol_to_id: Dict[str, str] = {
            entry["symbol"].lower(): cid
            for cid, entry in assets.items()
            if entry.get("symbol")
        }

        enriched = 0
        unmatched = []

        for _kraken_code, asset_info in raw.items():
            altname: str = asset_info.get("altname", "").strip()
            if not altname:
                continue

            # Skip pure fiat currencies (we only care about crypto assets)
            if altname in _FIAT_ALTNAMES:
                continue

            # Resolve: KNOWN_OVERRIDES first, then symbol lookup
            canonical_id: Optional[str] = (
                KNOWN_OVERRIDES.get(altname)
                or symbol_to_id.get(altname.lower())
            )

            if not canonical_id or canonical_id not in assets:
                unmatched.append(altname)
                continue

            entry = assets[canonical_id]

            # Set outgoing exchange symbol
            entry["exchange_symbols"]["kraken"] = altname

            # Add to incoming aliases so resolve("XBT") works directly
            alias_lower = altname.lower()
            if alias_lower not in entry["aliases"]:
                entry["aliases"].append(alias_lower)

            enriched += 1

        matched_symbols = [
            entry["exchange_symbols"]["kraken"]
            for entry in assets.values()
            if entry.get("exchange_symbols", {}).get("kraken")
        ]
        print(f"[KrakenSource] ✓ Enriched {enriched} assets with Kraken symbols")
        print(f"[KrakenSource]   Matched  ({len(matched_symbols)}): {sorted(matched_symbols)}")
        print(f"[KrakenSource]   Unmatched ({len(unmatched)}): {sorted(unmatched)}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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
            print(f"[KrakenSource]   Fetched {len(result)} Kraken assets")
            return result

        except requests.exceptions.RequestException as e:
            print(f"[KrakenSource] ✗ Request failed: {e}")
            return None
