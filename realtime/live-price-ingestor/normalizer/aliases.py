"""
Lightweight alias resolver for the ingestor service.

Reads data/coin_aliases.json and provides O(1) lookups from any
exchange symbol or name → canonical coin ID.

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
"""

import json
import logging
import os
from typing import Dict, Optional

import config

logger = logging.getLogger(__name__)


class AliasResolver:
    """
    Resolves exchange symbols/names to canonical coin IDs in O(1).

    Examples:
        resolve("XBT")      → "bitcoin"
        resolve("btc")      → "bitcoin"
        resolve("SOL")      → "solana"
        resolve("unknown")  → None
    """

    def __init__(self, json_path: str = config.ALIAS_JSON_PATH):
        self._json_path = os.path.abspath(json_path)
        self._lookup: Dict[str, str] = {}
        self._symbols: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        try:
            with open(self._json_path, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            logger.error(f"Alias map not found at {self._json_path}")
            logger.error("Run: python tools/populate_aliases/main.py")
            return
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in alias map: {e}")
            return

        assets = data.get("assets", {})

        for canonical_id, entry in assets.items():
            self._lookup[canonical_id.lower()] = canonical_id

            symbol = entry.get("symbol", "")
            if symbol:
                self._symbols[canonical_id] = symbol
                self._lookup[symbol.lower()] = canonical_id

            for alias in entry.get("aliases", []):
                self._lookup[alias.lower()] = canonical_id

            for sym in entry.get("exchange_symbols", {}).values():
                self._lookup[sym.lower()] = canonical_id

        meta = data.get("_meta", {})
        logger.info(
            f"Loaded {len(assets)} assets / {len(self._lookup)} lookup entries "
            f"(updated: {meta.get('updated_at', 'unknown')})"
        )

    def resolve(self, term: str) -> Optional[str]:
        if not term:
            return None
        return self._lookup.get(term.strip().lower())

    def reload(self) -> None:
        self._lookup.clear()
        self._symbols.clear()
        self._load()

    @property
    def total_aliases(self) -> int:
        return len(self._lookup)

    @property
    def total_assets(self) -> int:
        return len(set(self._lookup.values()))
