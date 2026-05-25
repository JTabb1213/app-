import csv

CORRECTIONS = {
    "aave":                      ("token",  "l1", "governance"),
    "algorand":                  ("pos",    "l1", "native"),
    "aptos":                     ("pos",    "l1", "native"),
    "arbitrum":                  ("rollup", "l2", "governance"),
    "avalanche-2":               ("pos",    "l1", "native"),
    "axie-infinity":             ("token",  "l1", "governance"),
    "basic-attention-token":     ("token",  "l1", "erc20"),
    "binancecoin":               ("pos",    "l1", "native"),
    "bitcoin":                   ("pow",    "l1", "native"),
    "bitcoin-cash":              ("pow",    "l1", "native"),
    "cardano":                   ("pos",    "l1", "native"),
    "chainlink":                 ("token",  "l1", "erc20"),
    "compound-governance-token": ("token",  "l1", "governance"),
    "cosmos":                    ("pos",    "l1", "native"),
    "curve-dao-token":           ("token",  "l1", "governance"),
    "decentraland":              ("token",  "l1", "erc20"),
    "dogecoin":                  ("pow",    "l1", "native"),
    "ethereum":                  ("pos",    "l1", "native"),
    "ethereum-classic":          ("pow",    "l1", "native"),
    "ethereum-name-service":     ("token",  "l1", "governance"),
    "fantom":                    ("pos",    "l1", "native"),
    "filecoin":                  ("hybrid", "l1", "native"),
    "havven":                    ("token",  "l1", "governance"),
    "hedera-hashgraph":          ("pos",    "l1", "native"),
    "hyperliquid":               ("pos",    "l1", "native"),
    "immutable-x":               ("rollup", "l2", "erc20"),
    "injective-protocol":        ("pos",    "l1", "native"),
    "kusama":                    ("pos",    "l1", "native"),
    "lido-dao":                  ("token",  "l1", "liquid_staking"),
    "litecoin":                  ("pow",    "l1", "native"),
    "loopring":                  ("rollup", "l2", "erc20"),
    "near":                      ("pos",    "l1", "native"),
    "ocean-protocol":            ("token",  "l1", "erc20"),
    "optimism":                  ("rollup", "l2", "governance"),
    "pepe":                      ("token",  "l1", "erc20"),
    "polkadot":                  ("pos",    "l1", "native"),
    "ripple":                    ("pos",    "l1", "native"),
    "shiba-inu":                 ("token",  "l1", "erc20"),
    "solana":                    ("pos",    "l1", "native"),
    "stellar":                   ("pos",    "l1", "native"),
    "sui":                       ("pos",    "l1", "native"),
    "sushi":                     ("token",  "l1", "governance"),
    "the-graph":                 ("token",  "l1", "erc20"),
    "the-open-network":          ("pos",    "l1", "native"),
    "the-sandbox":               ("token",  "l1", "erc20"),
    "thorchain":                 ("pos",    "l1", "native"),
    "tron":                      ("pos",    "l1", "native"),
    "uniswap":                   ("token",  "l1", "governance"),
    "yearn-finance":             ("token",  "l1", "governance"),
    "zcash":                     ("pow",    "l1", "native"),
}

COLUMNS = ['id','symbol','name','description','image_url','github_url','max_supply','consensus_type','network_layer','token_category']
path = 'data/coins_seed.csv'

with open(path, newline='') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

for row in rows:
    cid = row['id']
    if cid in CORRECTIONS:
        ct, nl, tc = CORRECTIONS[cid]
        row['consensus_type'] = ct
        row['network_layer']  = nl
        row['token_category'] = tc
    else:
        print(f"WARNING: no entry for {cid}")

with open(path, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)

print(f"Done: {len(rows)} rows updated")
