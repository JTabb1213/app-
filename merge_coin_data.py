import csv
from pathlib import Path

# Read the three source files
descriptions = {}
with open('data/coin_descriptions.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        descriptions[row['coin_name']] = row['description']

github_orgs = {}
with open('data/coins_github.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        github_orgs[row['coin_name']] = row['github']

max_supplies = {}
with open('data/coins_maxsupply.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Clean up: remove commas from numbers, handle "No max supply"
        ms = row['max_supply'].replace(',', '')
        if ms.lower() == 'no max supply':
            ms = ''
        max_supplies[row['coin_name']] = ms

# Read seed file and update
COLUMNS = ['id','symbol','name','description','image_url','github_url','max_supply','consensus_type','network_layer','token_category']

with open('data/coins_seed.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# Update with new data
for row in rows:
    symbol = row['symbol']
    
    if symbol in descriptions:
        row['description'] = descriptions[symbol]
    
    if symbol in github_orgs:
        row['github_url'] = github_orgs[symbol]
    
    if symbol in max_supplies:
        row['max_supply'] = max_supplies[symbol]

# Write back
with open('data/coins_seed.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)

print(f"Updated {len(rows)} coins with descriptions, github orgs, and max supplies")
