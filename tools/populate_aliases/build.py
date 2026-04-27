#!/usr/bin/env python3
"""
Combine symbols, coin_aliases, and exchange_symbols into data/coin_aliases.json.

Usage:
    python build.py                           # all coins from coin_aliases.json
    python build.py bitcoin cardano solana     # only specific coins
"""
import glob
import json
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # app/

COIN_ALIASES_PATH = os.path.join(SCRIPT_DIR, "sources", "coin_aliases", "coin_aliases.json")
SYMBOLS_PATH = os.path.join(SCRIPT_DIR, "sources", "symbols", "symbols.json")
EXCHANGE_SYMBOLS_DIR = os.path.join(SCRIPT_DIR, "sources", "exchange_symbols")
OUTPUT_PATH = os.path.join(ROOT_DIR, "data", "coin_aliases.json")


def load_exchange_mappings() -> dict[str, dict[str, str]]:
    """Load all exchange symbol source files into canonical_id -> symbol maps."""
    exchange_maps: dict[str, dict[str, str]] = {}
    pattern = os.path.join(EXCHANGE_SYMBOLS_DIR, "*_symbols.json")

    for path in glob.glob(pattern):
        name = os.path.basename(path)
        exchange = name.replace("_symbols.json", "").lower()

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_symbols = data.get("symbols", {})
        if not isinstance(raw_symbols, dict):
            continue

        exchange_map: dict[str, str] = {}
        for symbol, canonical_id in raw_symbols.items():
            if canonical_id is None:
                continue
            if canonical_id not in exchange_map:
                exchange_map[canonical_id] = symbol

        if exchange_map:
            exchange_maps[exchange] = exchange_map

    return exchange_maps


def main():
    # ── Load sources ──
    with open(COIN_ALIASES_PATH, "r", encoding="utf-8") as f:
        coin_aliases = json.load(f)["aliases"]

    with open(SYMBOLS_PATH, "r", encoding="utf-8") as f:
        symbols = json.load(f)["symbols"]

    exchange_maps = load_exchange_mappings()

    # ── Determine which coins to include ──
    if len(sys.argv) > 1:
        requested = sys.argv[1:]
        canonical_ids = []
        for cid in requested:
            if cid in coin_aliases:
                canonical_ids.append(cid)
            else:
                print(f"  ⚠ '{cid}' not found in coin_aliases.json, skipping")
    else:
        canonical_ids = list(coin_aliases.keys())

    # ── Build output ──
    output = {}
    exchange_counts = {exchange: 0 for exchange in exchange_maps}

    for cid in sorted(canonical_ids):
        entry = {
            "symbol": symbols.get(cid, "???"),
            "aliases": coin_aliases.get(cid, []),
            "exchange_symbols": {}
        }

        for exchange, exchange_map in exchange_maps.items():
            if cid in exchange_map:
                entry["exchange_symbols"][exchange] = exchange_map[cid]
                exchange_counts[exchange] += 1

        output[cid] = entry

    # ── Write ──
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"assets": output}, f, indent=4)
        f.write("\n")

    # ── Summary ──
    print(f"  ✓ Written {len(output)} coins to {OUTPUT_PATH}")
    print(f"    Symbols:  {sum(1 for e in output.values() if e['symbol'] != '???')}/{len(output)}")
    for exchange, count in sorted(exchange_counts.items()):
        print(f"    {exchange.capitalize():10s}: {count}/{len(output)}")


if __name__ == "__main__":
    main()
