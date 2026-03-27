"""
In-process alias resolver backed by data/coin_aliases.json.

Loads once at startup; resolves any term → canonical coin ID in O(1).
This replaces Redis-based alias lookups for static mappings.

JSON schema:
  {
    "assets": {
      "bitcoin": {
        "symbol":          "BTC",
        "aliases":         ["bitcoin", "btc", "xbt"],
        "exchange_symbols": { "kraken": "XBT" }
      }
    }
  }

The resolver builds its lookup dict with clear priority:
  1. canonical_id       → itself
  2. symbol             → canonical_id
  3. aliases[]          → canonical_id
  4. exchange_symbols values → canonical_id  (highest priority, applied last)

To refresh the alias map, run:
    python tools/populate_aliases/main.py
Then call alias_resolver.reload() or restart the app.
"""

import json
import os
from typing import Dict, Optional

# Resolved relative to this file: backend/services/alias/resolver.py
# → data file is at:             <project-root>/data/coin_aliases.json
_DEFAULT_JSON_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "data", "coin_aliases.json"
)


class AliasResolver:
    """
    Resolves any coin identifier (symbol, name, exchange-specific code)
    to a canonical coin ID in O(1) time using an in-memory dict.

    Two lookup directions are supported:

    1. Incoming  (exchange data → canonical):
         resolve("XBT")             → "bitcoin"
         resolve("btc")             → "bitcoin"
         resolve("Bitcoin")         → "bitcoin"

    2. Outgoing  (canonical → exchange-specific symbol):
         get_exchange_symbol("bitcoin", "kraken")  → "XBT"
         get_exchange_symbol("bitcoin", "coinbase") → None  (falls back to BTC)
    """

    def __init__(self, json_path: str = _DEFAULT_JSON_PATH):
        self._json_path = os.path.abspath(json_path)
        # alias_lower  →  canonical_id
        self._lookup: Dict[str, str] = {}
        # canonical_id  →  {exchange_lower: exchange_symbol}
        self._exchange_symbols: Dict[str, Dict[str, str]] = {}
        # canonical_id  →  standard uppercase symbol (e.g. "bitcoin" → "BTC")
        self._standard_symbols: Dict[str, str] = {}
        self._load()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load the JSON file and build in-memory lookup dicts."""
        try:
            with open(self._json_path, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"[AliasResolver] ✗ Alias map not found at {self._json_path}")
            print("[AliasResolver]   Run tools/populate_aliases/main.py to generate it.")
            return
        except json.JSONDecodeError as e:
            print(f"[AliasResolver] ✗ Invalid JSON in alias map: {e}")
            return

        assets: Dict = data.get("assets", {})

        for canonical_id, entry in assets.items():
            # 1. canonical_id always resolves to itself
            self._lookup[canonical_id.lower()] = canonical_id

            # 2. Standard symbol → canonical_id (e.g. "btc" → "bitcoin")
            symbol = entry.get("symbol", "")
            if symbol:
                self._standard_symbols[canonical_id] = symbol
                self._lookup[symbol.lower()] = canonical_id

            # 3. All curated/auto-derived aliases
            for alias in entry.get("aliases", []):
                self._lookup[alias.lower()] = canonical_id

            # Cache exchange symbol map for outgoing direction
            exchanges: Dict[str, str] = entry.get("exchange_symbols", {})
            if exchanges:
                self._exchange_symbols[canonical_id] = {
                    ex.lower(): sym for ex, sym in exchanges.items()
                }

            # 4. Exchange symbols → canonical_id (highest priority, applied last)
            # These are curated overrides (e.g. Kraken's "XBT" → "bitcoin").
            # Applied after alias registration so they always win.
            for sym in exchanges.values():
                self._lookup[sym.lower()] = canonical_id

        meta = data.get("_meta", {})
        print(
            f"[AliasResolver] ✓ Loaded {len(assets)} assets / "
            f"{len(self._lookup)} lookup entries "
            f"(updated: {meta.get('updated_at', 'unknown')})"
        )

    def reload(self) -> None:
        """
        Reload the alias map from disk without restarting the app.
        Call this after running tools/populate_aliases/main.py.
        """
        self._lookup.clear()
        self._exchange_symbols.clear()
        self._standard_symbols.clear()
        self._load()

    # ------------------------------------------------------------------
    # Incoming direction: any term → canonical ID
    # ------------------------------------------------------------------

    def resolve(self, term: str) -> Optional[str]:
        """
        Resolve any alias/symbol/name to its canonical coin ID.

        Examples:
            resolve("XBT")       → "bitcoin"   (Kraken exchange code)
            resolve("btc")       → "bitcoin"   (standard symbol)
            resolve("Bitcoin")   → "bitcoin"   (display name)
            resolve("bitcoin")   → "bitcoin"   (canonical ID = itself)
            resolve("SOL")       → "solana"
            resolve("unknown")   → None

        Args:
            term: Any coin identifier — case-insensitive.

        Returns:
            Canonical coin ID (CoinGecko convention) or None if not found.
        """
        if not term:
            return None
        return self._lookup.get(term.strip().lower())

    def resolve_from_exchange(self, exchange_symbol: str, exchange: str) -> Optional[str]:
        """
        Convenience wrapper for parsing incoming WebSocket/REST data from an
        exchange that uses non-standard symbols.

        Identical to resolve() since exchange symbols are registered in the
        lookup dict at load time, but more expressive at the call site:

            resolve_from_exchange("XBT", "kraken")  → "bitcoin"

        Args:
            exchange_symbol: Symbol as used by the exchange (e.g. "XBT").
            exchange: Exchange name — currently unused but kept for clarity
                      and potential future per-exchange disambiguation.

        Returns:
            Canonical coin ID or None.
        """
        return self.resolve(exchange_symbol)

    # ------------------------------------------------------------------
    # Outgoing direction: canonical ID → exchange-specific symbol
    # ------------------------------------------------------------------

    def get_exchange_symbol(self, canonical_id: str, exchange: str) -> Optional[str]:
        """
        Get the symbol used by a specific exchange for a given coin.

        Use this when building outgoing messages/orders to an exchange so
        you send the symbol the exchange actually understands.

        Examples:
            get_exchange_symbol("bitcoin", "kraken")   → "XBT"
            get_exchange_symbol("ethereum", "kraken")  → None  (ETH is standard)
            get_exchange_symbol("solana", "kraken")    → None  (SOL is standard)

        Args:
            canonical_id: The canonical coin ID (e.g. "bitcoin").
            exchange: Exchange name, case-insensitive (e.g. "kraken").

        Returns:
            Exchange-specific symbol string, or None if the coin uses the
            standard symbol on that exchange (or is unknown).
        """
        exchange_map = self._exchange_symbols.get(canonical_id, {})
        return exchange_map.get(exchange.lower())

    def get_exchange_symbol_or_default(self, canonical_id: str, exchange: str) -> Optional[str]:
        """
        Like get_exchange_symbol() but falls back to the asset's standard
        symbol when no exchange-specific override exists.

        Returns None only if the canonical_id is unknown.
        """
        override = self.get_exchange_symbol(canonical_id, exchange)
        if override:
            return override
        return self._standard_symbols.get(canonical_id)

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    @property
    def total_aliases(self) -> int:
        """Total number of registered lookup entries."""
        return len(self._lookup)

    @property
    def total_assets(self) -> int:
        """Total number of distinct canonical assets."""
        return len(set(self._lookup.values()))


# ---------------------------------------------------------------------------
# Module-level singleton — loaded once when the module is first imported.
# All services should import this instance rather than creating their own.
# ---------------------------------------------------------------------------
alias_resolver = AliasResolver()
