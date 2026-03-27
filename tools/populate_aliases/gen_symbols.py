#!/usr/bin/env python3
"""One-shot script to generate sources/symbols/symbols.json from kraken_symbols.json."""
import json, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(SCRIPT_DIR, "sources/exchange_symbols/kraken_symbols.json")) as f:
    kraken = json.load(f)["symbols"]

with open(os.path.join(SCRIPT_DIR, "sources/coin_aliases/coin_aliases.json")) as f:
    aliases = json.load(f)["aliases"]

# Invert kraken: altname -> canonical_id  =>  canonical_id -> altname
inv = {}
for altname, cid in kraken.items():
    if cid is not None and cid not in inv:
        inv[cid] = altname

# Overrides for well-known standard tickers
overrides = {
    "bitcoin": "BTC",
    "dogecoin": "DOGE",
}
inv.update(overrides)

missing = [cid for cid in aliases if cid not in inv]
if missing:
    print(f"WARNING: {len(missing)} coins in coin_aliases without a symbol: {missing[:10]}")

symbols = {cid: inv[cid] for cid in sorted(inv) if cid in aliases}
print(f"Total symbols: {len(symbols)}")
print(f"Coverage: {len(symbols)}/{len(aliases)}")

output = {
    "_meta": {
        "description": "Canonical ID to display symbol mapping. Derived from exchange symbols with manual overrides.",
        "updated_at": "2026-03-26"
    },
    "symbols": symbols
}

out_dir = os.path.join(SCRIPT_DIR, "sources/symbols")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "symbols.json")
with open(out_path, "w") as f:
    json.dump(output, f, indent=4)
    f.write("\n")
print(f"Written to {out_path}")
