"""
CoinGecko alias source.

Builds the canonical asset list by fetching the top N coins by market cap
from CoinGecko's /coins/markets endpoint.  This is the *primary* source:
it establishes the canonical IDs (matching CoinGecko convention) used as
keys throughout the alias map and the rest of the app.
"""

import math
import time
import requests
from typing import Dict, List, Optional

from .base import BaseAliasSource, AssetsDict

_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
_LIST_URL    = "https://api.coingecko.com/api/v3/coins/list"
_PER_PAGE = 250  # CoinGecko max per page


class CoinGeckoSource(BaseAliasSource):
    """Fetches coins from CoinGecko and builds the base assets dict.

    Two modes:
      top_n=N   (default) — fetches top N by market cap via /coins/markets.
                            Use when you want ranked coins with market data.
      top_n=-1            — fetches ALL ~15,000 coins via /coins/list in a
                            single request.  No market cap ranking, but
                            maximum coverage.  Pass --top -1 on the CLI.
    """

    SOURCE_NAME = "coingecko"

    def __init__(self, top_n: int = 500, request_delay: float = 1.5):
        """
        Args:
            top_n: Number of top coins by market cap to include.
                   Pass -1 to fetch every coin CoinGecko knows about.
            request_delay: Seconds to wait between paginated requests
                           (respects CoinGecko free-tier rate limits).
        """
        self.top_n = top_n
        self.request_delay = request_delay

    # ------------------------------------------------------------------
    # BaseAliasSource interface
    # ------------------------------------------------------------------

    def enrich(self, assets: AssetsDict) -> None:
        """
        Populate the assets dict with entries fetched from CoinGecko.

        For each coin the following entry is created:
        {
            "symbol":       "BTC",
            "aliases":      ["btc", "bitcoin"],   # id + symbol + name (lowercased)
            "exchange_symbols": {}                # filled in by exchange sources
        }
        """
        if self.top_n == -1:
            coins = self._fetch_all_coins()
        else:
            coins = self._fetch_top_coins()
        if not coins:
            print("[CoinGeckoSource] ✗ No coins fetched — assets dict unchanged.")
            return

        added = 0
        for coin in coins:
            canonical_id = coin.get("id")
            symbol = (coin.get("symbol") or "").upper()
            name = (coin.get("name") or "")

            if not canonical_id:
                continue

            # Build alias list: id + symbol + lowercased name
            aliases = list({
                canonical_id.lower(),
                symbol.lower(),
                name.lower(),
            })

            assets[canonical_id] = {
                "symbol": symbol,
                "aliases": aliases,
                "exchange_symbols": {},
            }
            added += 1

        label = "all" if self.top_n == -1 else f"top-{self.top_n}"
        print(f"[CoinGeckoSource] ✓ Built {added} assets from CoinGecko ({label})")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_all_coins(self) -> List[Dict]:
        """
        Fetch every coin CoinGecko knows about via /coins/list.
        Returns a list of {id, symbol, name} dicts.
        This is a single HTTP call — no pagination, no rate limit concerns.
        """
        try:
            print("[CoinGeckoSource] Fetching full coin list from /coins/list...")
            resp = requests.get(_LIST_URL, timeout=30)
            resp.raise_for_status()
            coins = resp.json()
            print(f"[CoinGeckoSource]   Received {len(coins)} coins")
            return coins
        except Exception as e:
            print(f"[CoinGeckoSource] ✗ Failed to fetch /coins/list: {e}")
            return []

    def _fetch_top_coins(self) -> List[Dict]:
        """Fetch top_n coins across multiple paginated requests."""
        all_coins: List[Dict] = []
        pages = math.ceil(self.top_n / _PER_PAGE)

        for page in range(1, pages + 1):
            remaining = self.top_n - len(all_coins)
            per_page = min(_PER_PAGE, remaining)

            coins = self._fetch_page(page, per_page)
            if coins is None:
                print(f"[CoinGeckoSource] ✗ Stopping after page {page - 1} due to error.")
                break

            all_coins.extend(coins)
            print(f"[CoinGeckoSource]   Page {page}/{pages}: fetched {len(coins)} coins "
                  f"(total so far: {len(all_coins)})")

            if len(coins) < per_page:
                # CoinGecko returned fewer coins than requested — we've hit the end
                break

            if page < pages:
                time.sleep(self.request_delay)

        return all_coins

    def _fetch_page(self, page: int, per_page: int) -> Optional[List[Dict]]:
        """Fetch a single page from /coins/markets."""
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": page,
            "sparkline": "false",
        }
        try:
            resp = requests.get(_MARKETS_URL, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:
                print(f"[CoinGeckoSource] ⚠ Rate limited on page {page} — "
                      "waiting 60s before retry...")
                time.sleep(60)
                return self._fetch_page(page, per_page)  # one retry
            print(f"[CoinGeckoSource] ✗ HTTP error on page {page}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[CoinGeckoSource] ✗ Request failed on page {page}: {e}")
            return None
