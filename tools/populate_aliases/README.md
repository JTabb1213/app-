# populate_aliases

Standalone script that fetches coin metadata from configured API sources and
writes `data/coin_aliases.json` — the file the backend reads at
startup for all alias resolution.

---

## Quick start

```bash
cd tools/populate_aliases
pip install requests          # only dependency
python main.py                # CoinGecko top 500 + Kraken, writes to data/
```

After running, restart the backend **or** hit `POST /api/reload-aliases` to
hot-reload without a restart.

---

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--sources` | `coingecko kraken` | Sources to run, in order |
| `--top N` | `500` | Top N coins by market cap from CoinGecko |
| `--out PATH` | `data/coin_aliases.json` | Output file path |
| `--dry-run` | off | Fetch & summarise without writing |

```bash
# Examples
python main.py --top 100                        # smaller, faster
python main.py --sources coingecko              # skip Kraken
python main.py --dry-run                        # preview only
python main.py --out /tmp/test_aliases.json     # custom output
```

---

## Adding a new exchange

1. Create `sources/<exchange>.py` — copy `sources/kraken.py` as a template.
2. Subclass `BaseAliasSource` and implement `enrich(assets)`.
3. Add two lines to `main.py`:

```python
# In _build_registry():
from sources.myexchange import MyExchangeSource
return {
    ...
    "myexchange": MyExchangeSource,
}
```

4. Run:
```bash
python main.py --sources coingecko kraken myexchange
```

### What `enrich()` should do

- **Do NOT** create new canonical entries (CoinGecko is the authority).
- **Do** set `assets[canonical_id]["exchange_symbols"]["<exchange>"] = "<symbol>"`.
- **Do** append exchange-specific symbols to `aliases` so the resolver can
  map incoming WebSocket data without any extra logic.

### Matching exchange symbols → canonical IDs

Use the helper pattern from `KrakenSource`:

```python
# 1. Build a symbol → canonical_id map from the assets already in the dict
symbol_to_id = {
    entry["symbol"].lower(): cid
    for cid, entry in assets.items()
    if entry.get("symbol")
}

# 2. Add KNOWN_OVERRIDES for symbols that differ from the standard
KNOWN_OVERRIDES = {
    "EXCHANGE_CODE": "canonical_id",  # e.g. "XBT": "bitcoin"
}

# 3. Resolve
canonical_id = KNOWN_OVERRIDES.get(altname) or symbol_to_id.get(altname.lower())
```

---

## Output format

```json
{
  "_meta": {
    "version": "1",
    "updated_at": "2026-03-16T00:00:00+00:00",
    "sources": ["coingecko", "kraken"],
    "top_n": 500
  },
  "assets": {
    "bitcoin": {
      "symbol": "BTC",
      "coingecko_id": "bitcoin",
      "aliases": ["btc", "xbt", "bitcoin"],
      "exchange_symbols": {
        "kraken": "XBT"
      }
    }
  }
}
```

| Field | Purpose |
|-------|---------|
| `symbol` | Standard uppercase symbol (BTC, ETH, …) |
| `coingecko_id` | Canonical ID used as the dict key and in the database |
| `aliases` | All strings that resolve to this asset (incoming direction) |
| `exchange_symbols` | Per-exchange symbols for outgoing messages/orders |
