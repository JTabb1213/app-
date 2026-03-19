#!/usr/bin/env python3
"""
Populate (or refresh) data/coin_aliases.json from external API sources.

Usage:
    # Full refresh — CoinGecko top 500 + Kraken symbols  (recommended)
    python main.py

    # Only CoinGecko, top 100 coins
    python main.py --sources coingecko --top 100

    # CoinGecko + Kraken, custom output path
    python main.py --sources coingecko kraken --out /path/to/my_aliases.json

    # Preview without writing (dry run)
    python main.py --dry-run

Adding a new exchange later:
    1. Create  tools/populate_aliases/sources/<exchange>.py
    2. Subclass BaseAliasSource and implement enrich()
    3. Add it to SOURCE_REGISTRY below
    4. Run:  python main.py --sources coingecko <exchange>

This script is intentionally standalone — it has no dependency on the backend
application code. It only needs the 'requests' library (pip install requests).
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List

# ---------------------------------------------------------------------------
# Path setup — resolve the default output path relative to this file
# ---------------------------------------------------------------------------
_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_TOOLS_DIR, "..", ".."))
DEFAULT_OUTPUT = os.path.join(_PROJECT_ROOT, "data", "coin_aliases.json")

# ---------------------------------------------------------------------------
# Source registry — add new exchange sources here
# ---------------------------------------------------------------------------
# Import lazily inside main() so missing optional deps don't break --help
def _build_registry():
    from sources.coingecko import CoinGeckoSource
    from sources.kraken import KrakenSource

    return {
        "coingecko": CoinGeckoSource,
        "kraken": KrakenSource,
        # "coinbase": CoinbaseSource,   # ← add future exchanges here
        # "binance":  BinanceSource,
    }


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def build_assets(
    source_names: List[str],
    top_n: int,
    preloaded: Dict[str, dict] = None,
) -> Dict[str, dict]:
    """
    Run each source in order and return the merged assets dict.

    CoinGecko must be first when building from scratch.
    Pass preloaded to start from an existing assets dict (enrich-only mode).
    """
    registry = _build_registry()
    assets: Dict[str, dict] = dict(preloaded) if preloaded else {}

    for name in source_names:
        cls = registry.get(name)
        if cls is None:
            print(f"[main] ⚠ Unknown source '{name}' — skipping. "
                  f"Available: {list(registry.keys())}")
            continue

        print(f"\n[main] ── Running source: {name} ──")

        # CoinGeckoSource accepts top_n; exchange sources don't need it
        if name == "coingecko":
            source = cls(top_n=top_n)
        else:
            source = cls()

        source.enrich(assets)

    return assets


def write_output(assets: Dict[str, dict], source_names: List[str],
                 top_n: int, output_path: str) -> None:
    """Write the final JSON file."""
    output = {
        "_meta": {
            "version": "1",
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "sources": source_names,
            "top_n": top_n,
            "description": (
                "Canonical coin alias map. "
                "Run tools/populate_aliases/main.py to refresh."
            ),
        },
        "assets": assets,
    }

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, sort_keys=True)

    print(f"\n[main] ✓ Written {len(assets)} assets → {output_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Populate backend/data/coin_aliases.json from API sources.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        default=["coingecko", "kraken"],
        metavar="SOURCE",
        help=(
            "Sources to run in order. CoinGecko must be first. "
            "Default: coingecko kraken"
        ),
    )
    parser.add_argument(
        "--top",
        type=int,
        default=500,
        metavar="N",
        help=(
            "Number of top coins by market cap to fetch from CoinGecko. "
            "Default: 500. Pass -1 to fetch ALL coins (~15,000) via /coins/list."
        ),
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_OUTPUT,
        metavar="PATH",
        help=f"Output JSON path. Default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch data and print a summary without writing the output file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print(f"[main] Sources : {args.sources}")
    print(f"[main] Top N   : {args.top}")
    print(f"[main] Output  : {args.out}")
    print(f"[main] Dry run : {args.dry_run}")

    # ------------------------------------------------------------------
    # If CoinGecko is not in sources, load the existing file so exchange
    # sources have existing assets to enrich (instead of starting empty).
    # ------------------------------------------------------------------
    preloaded: Dict[str, dict] = {}
    if "coingecko" not in args.sources:
        if os.path.exists(args.out):
            with open(args.out, "r") as f:
                existing = json.load(f)
            preloaded = existing.get("assets", {})
            print(f"[main] Loaded {len(preloaded)} existing assets from {args.out}")
            print("[main] Skipping CoinGecko — enriching existing data only.")
        else:
            print(f"[main] ⚠ No existing file at {args.out} and 'coingecko' not in sources.")
            print("[main]   Run with 'coingecko' first to build the base asset list.")
            sys.exit(1)

    assets = build_assets(args.sources, args.top, preloaded)

    if not assets:
        print("[main] ✗ No assets built — check source errors above.")
        sys.exit(1)

    # Summary stats
    total_aliases = sum(len(e.get("aliases", [])) for e in assets.values())
    exchanges_covered = set()
    for entry in assets.values():
        exchanges_covered.update(entry.get("exchange_symbols", {}).keys())

    print(f"\n[main] ── Summary ──")
    print(f"  Assets          : {len(assets)}")
    print(f"  Total aliases   : {total_aliases}")
    print(f"  Exchanges mapped: {exchanges_covered or '(none)'}")

    if args.dry_run:
        print("\n[main] Dry run — file not written.")
        return

    write_output(assets, args.sources, args.top, args.out)
    print("[main] Done. Restart the backend (or call /api/reload-aliases) to pick up changes.")


if __name__ == "__main__":
    # Run from the tools/populate_aliases/ directory so relative imports work
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
