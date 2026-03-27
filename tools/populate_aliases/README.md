main.py  ──► 1. sources/coingecko.py
             │   └─ calls CoinGecko /coins/markets?top=N
             │   └─ creates assets dict: { canonical_id: {symbol, aliases:[], exchange_symbols:{}} }
             │
             ├─► 2. sources/coin_aliases.py
             │   └─ reads sources/coin_aliases/coin_aliases.json  
             │   └─ for each coin in the list, REPLACES aliases[] with the curated list
             │   └─ coins not in this file keep auto-derived [id, symbol, name]
             │
             └─► 3. sources/kraken.py
                 └─ reads sources/exchange_symbols/kraken_symbols.json
                 └─ sets exchange_symbols["kraken"] on matching assets

Final output ──► data/coin_aliases.json
                 │
                 ├─ backend/services/alias/resolver.py   (backend API)
                 └─ realtime/normalizer/aliases.py        (realtime WebSocket pipeline)

###################################################################
Other tool to combine manually created exchange aliases, coin_aliases, and normal symbols is to run build.py, arguments are canonical id's and can be separated by a space (example: bitcoin cardano avalanche-2). Only those coins will be included in the final json file