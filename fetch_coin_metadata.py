#!/usr/bin/env python3
"""
Fetch max_supply and github_url for each coin from CoinGecko.
- Does NOT overwrite image_url (preserves existing local paths or URLs)
- Writes exactly the 9 expected columns with no extra commas
- Uses per-coin /coins/{id} since /coins/markets doesn't return max_supply or github_url
"""

import csv
import requests
import time
import sys

CSV_FILE = "/Users/jacktabb/Desktop/app/data/coins_seed.csv"
COINGECKO_API = "https://api.coingecko.com/api/v3/coins"
COLUMNS = ['id', 'symbol', 'name', 'description', 'image_url', 'github_url', 'max_supply', 'consensus_type', 'network_layer']

# Local coin IDs that differ from CoinGecko IDs
COINGECKO_ID_MAP = {
    "havven": "synthetix",
}

def get_gecko_id(coin_id):
    return COINGECKO_ID_MAP.get(coin_id, coin_id)

def fetch_coin(coin_id, retries=4):
    gecko_id = get_gecko_id(coin_id)
    url = f"{COINGECKO_API}/{gecko_id}"
    params = {
        "localization": "false",
        "tickers": "false",
        "market_data": "true",
        "community_data": "false",
        "developer_data": "false",
        "sparkline": "false",
    }
    backoff = 2
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 429:
                wait = backoff ** attempt * 5
                print(f" rate limited, waiting {wait}s...", end='', flush=True)
                time.sleep(wait)
                continue
            if resp.status_code == 404:
                print(f" 404 not found", end='', flush=True)
                return {}
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(backoff ** attempt * 2)
            else:
                print(f" error: {e}", end='', flush=True)
    return {}

def extract(data):
    # max_supply: hard cap only, blank if infinite/unknown (e.g. ETH, DOGE)
    max_supply = data.get("market_data", {}).get("max_supply")
    max_supply = str(int(max_supply)) if max_supply is not None else ""

    # github_url: first repo link
    github_url = ""
    repos = data.get("links", {}).get("repos_url", {}).get("github", [])
    if repos:
        github_url = repos[0]

    return max_supply, github_url

def run():
    with open(CSV_FILE, newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Only process coins missing max_supply or github_url
    missing = [r for r in rows if not r.get('max_supply') or not r.get('github_url')]
    skipped = len(rows) - len(missing)

    print(f"{skipped} coins already complete, {len(missing)} need fetching\n")

    if not missing:
        print("✓ Nothing to do.")
        return

    for i, row in enumerate(missing):
        coin_id = row['id']
        print(f"[{i+1:2}/{len(missing)}] {coin_id:35s}", end=' ', flush=True)

        data = fetch_coin(coin_id)

        if data:
            max_supply, github_url = extract(data)
            row['max_supply'] = max_supply
            row['github_url'] = github_url
            print(f"max={max_supply or 'unlimited':20s} github={'yes' if github_url else 'no'}")
        else:
            print("skipped")

        # Convert image_url to local path if it's still a CoinGecko URL
        img_url = row.get('image_url', '')
        if img_url and img_url.startswith('https://'):
            ext = '.png'
            if '.jpg' in img_url.lower():
                ext = '.jpg'
            elif '.jpeg' in img_url.lower():
                ext = '.jpeg'
            elif '.gif' in img_url.lower():
                ext = '.gif'
            row['image_url'] = f"/images/coins/{coin_id}{ext}"

        # Free tier: ~10 req/min
        time.sleep(4)

    # Write exactly COLUMNS — extrasaction='ignore' drops any stray keys
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✓ Saved to {CSV_FILE}")


if __name__ == '__main__':
    run()

