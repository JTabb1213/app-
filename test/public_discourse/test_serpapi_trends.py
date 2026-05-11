"""
test_serpapi_trends.py
======================
Fetches Google search trends and keyword data using SerpAPI.
More reliable than pytrends because it uses official Google endpoints.

SerpAPI Google Trends Engine:
  ────────────────────────────
  What it returns:
    - interest_over_time: relative interest (0-100) over the last 12 months
    - related_queries: keywords people search alongside your query
    - interest_by_region: which countries/regions show the most interest
    - CPC & competition data: advertiser metrics (paid plans)

  How far back:
    - Default: last 12 months of weekly data
    - Can be customized with 'date_from' and 'date_to' parameters
    - Data is updated daily

  Cost per request:
    - FREE tier: 100 requests/month (includes batching!)
    - Paid: $0.005-0.02 per request depending on volume

  Batching:
    - You can query multiple keywords in ONE request with comma-separated values
    - Example: "bitcoin,ethereum,solana" in a single API call
    - This dramatically reduces your monthly API quota usage
    - Instead of 5 requests for 5 coins, you only use 1 request!

Example:
  - Single keyword: 5 coins = 5 API calls
  - Batched (5 coins/request): 5 coins = 1 API call ← 80% SAVINGS!

Sign up at https://serpapi.com (100 free monthly API credits).

Install:
    pip install requests

Usage:
    export SERPAPI_KEY=your_key_here
    python3 test_serpapi_trends.py
"""

import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# ── Env loading ─────────────────────────────────────────────────────────────────
root_env = Path(__file__).resolve().parents[2] / ".env"
if root_env.exists():
    load_dotenv(root_env, override=False)

# ── Config ────────────────────────────────────────────────────────────────────

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
SERPAPI_BASE_URL = os.getenv("SERPAPI_BASE_URL", "https://serpapi.com/search")

COINS = [
    "bitcoin",
    "ethereum",
    "solana",
    "cardano",
    "chainlink",
]

# Batch size: how many keywords to query per API request
# SerpAPI allows batching, so we can query multiple keywords in one call
BATCH_SIZE = 5  # 5 keywords per request = 1 API call instead of 5

HEADERS = {"User-Agent": "crypto-search-trends/1.0"}


# ── Google Trends via SerpAPI (BATCHED) ─────────────────────────────────────

def fetch_google_trends_batch(keywords: list[str]) -> dict:
    """
    Fetch Google Trends data for multiple keywords in a SINGLE API request.

    Batching saves API quota dramatically:
      - 5 keywords in 1 batch = 1 API call (vs 5 calls if done individually)
      - Saves 80% of your monthly quota for the same data!

    Args:
        keywords: list of keyword strings, e.g., ["bitcoin", "ethereum"]

    Returns:
        dict mapping each keyword to its trend data, or None on failure
    """
    if not SERPAPI_KEY:
        raise RuntimeError(
            "SERPAPI_KEY not set. Get a free key at https://serpapi.com "
            "and set it in .env"
        )

    # Batch keywords: comma-separated query
    query = ",".join(keywords)

    params = {
        "engine":       "google_trends",
        "q":            query,              # Multiple keywords, comma-separated
        "api_key":      SERPAPI_KEY,
    }

    try:
        resp = requests.get(SERPAPI_BASE_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            print(f"    SerpAPI error: {data['error']}")
            return None

        return data
    except requests.RequestException as e:
        print(f"    Request error: {e}")
        return None


def parse_trends_response(data: dict, keyword: str) -> dict:
    """
    Extract key metrics from SerpAPI Google Trends response for a single keyword.

    Actual response structure:
      interest_over_time:
        timeline_data: [
          {
            date: "May 4–10, 2025",
            timestamp: "1746316800",
            values: [
              { query: "bitcoin",   value: "33", extracted_value: 33 },
              { query: "ethereum",  value: "5",  extracted_value: 5  },
              ...
            ]
          },
          ...
        ]
    """
    if not data:
        return None

    timeline_data = data.get("interest_over_time", {}).get("timeline_data", [])
    if not timeline_data:
        return None

    # Extract this keyword's value from each time period
    datapoints = []
    for period in timeline_data:
        match = next(
            (v for v in period.get("values", []) if v.get("query", "").lower() == keyword.lower()),
            None
        )
        if match:
            datapoints.append({
                "date":  period.get("date"),
                "value": match.get("extracted_value", 0),
            })

    if not datapoints:
        return None

    values = [p["value"] for p in datapoints]
    return {
        "keyword":       keyword,
        "latest_value":  values[-1],
        "peak_value":    max(values),
        "average_value": round(sum(values) / len(values), 2),
        "datapoints":    datapoints,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    if not SERPAPI_KEY:
        print("ERROR: SERPAPI_KEY is not set.")
        print("Get a free key at https://serpapi.com (100 free monthly requests)")
        print("Then add it to your .env:")
        print("  SERPAPI_KEY=your_key_here")
        exit(1)

    print("=" * 60)
    print("SerpAPI Google Trends — Crypto Search Interest (BATCHED)")
    print(f"Batch size: {BATCH_SIZE} keywords per request")
    print("=" * 60)

    results = []

    # Batch the keywords: 5 coins per request instead of 1 coin per request
    for i in range(0, len(COINS), BATCH_SIZE):
        batch = COINS[i : i + BATCH_SIZE]
        print(f"\nFetching batch: {batch} (1 API call for {len(batch)} keywords)")

        # Single API call for the entire batch
        data = fetch_google_trends_batch(batch)

        if data:
            # Parse results for each keyword in the batch
            for coin in batch:
                parsed = parse_trends_response(data, coin)
                if parsed:
                    results.append(parsed)

                    print(f"\n  {coin.upper()}")
                    if parsed.get("latest_value") is not None:
                        print(f"    Latest value  : {parsed['latest_value']} / 100")
                        print(f"    Peak value    : {parsed['peak_value']} / 100")
                        print(f"    Average value : {parsed['average_value']} / 100")
                        print(f"    Data points   : {len(parsed['datapoints'])}")
                        if parsed.get("top_regions"):
                            print(f"    Top regions   :")
                            for region in parsed["top_regions"]:
                                print(f"      {region['region']:20s}  {region['value']}")
                    else:
                        print("    No trend data available.")
                else:
                    print(f"\n  {coin.upper()} — no data in batch response")
        else:
            print("  Failed to fetch batch.")

        # Polite rate limiting between batches
        if i + BATCH_SIZE < len(COINS):
            time.sleep(1)

    print("\n" + "=" * 60)
    print(f"SUMMARY: {len(COINS)} keywords fetched in {(len(COINS) + BATCH_SIZE - 1) // BATCH_SIZE} API call(s)")
    print(f"SAVINGS: Without batching, this would have taken {len(COINS)} calls!")
    print("=" * 60)

    print("\n── Full JSON output (bitcoin) ───────────────────────────────")
    btc = next((r for r in results if r.get("keyword").lower() == "bitcoin"), None)
    if btc:
        summary = {k: v for k, v in btc.items() if k != "raw"}
        print(json.dumps(summary, indent=2))
