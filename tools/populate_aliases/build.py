#!/usr/bin/env python3
"""
Combine symbols, coin_aliases, and exchange_symbols into data/coin_aliases.json.

Usage:
    python build.py                           # all coins from coin_aliases.json
    python build.py bitcoin cardano solana     # only specific coins
"""
import json
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # app/

COIN_ALIASES_PATH = os.path.join(SCRIPT_DIR, "sources", "coin_aliases", "coin_aliases.json")
KRAKEN_SYMBOLS_PATH = os.path.join(SCRIPT_DIR, "sources", "exchange_symbols", "kraken_symbols.json")
SYMBOLS_PATH = os.path.join(SCRIPT_DIR, "sources", "symbols", "symbols.json")
OUTPUT_PATH = os.path.join(ROOT_DIR, "data", "coin_aliases.json")


def main():
    # ── Load sources ──
    with open(COIN_ALIASES_PATH) as f:
        coin_aliases = json.load(f)["aliases"]

    with open(KRAKEN_SYMBOLS_PATH) as f:
        kraken_raw = json.load(f)["symbols"]

    with open(SYMBOLS_PATH) as f:
        symbols = json.load(f)["symbols"]

    # Invert kraken: altname -> canonical_id  =>  canonical_id -> altname
    kraken_map = {}
    for altname, canonical_id in kraken_raw.items():
        if canonical_id is not None and canonical_id not in kraken_map:
            kraken_map[canonical_id] = altname

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
    for cid in sorted(canonical_ids):
        entry = {
            "symbol": symbols.get(cid, "???"),
            "aliases": coin_aliases.get(cid, []),
            "exchange_symbols": {}
        }
        if cid in kraken_map:
            entry["exchange_symbols"]["kraken"] = kraken_map[cid]
        output[cid] = entry

    # ── Write ──
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump({"assets": output}, f, indent=4)
        f.write("\n")

    # ── Summary ──
    with_kraken = sum(1 for e in output.values() if e["exchange_symbols"])
    print(f"  ✓ Written {len(output)} coins to {OUTPUT_PATH}")
    print(f"    Symbols:  {sum(1 for e in output.values() if e['symbol'] != '???')}/{len(output)}")
    print(f"    Kraken:   {with_kraken}/{len(output)}")


if __name__ == "__main__":
    main()
