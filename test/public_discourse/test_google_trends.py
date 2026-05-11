"""
test_google_trends.py
=====================
Fetches relative search interest for crypto coins using Google Trends.
No API key required — uses the unofficial pytrends library.

Install:
    pip install pytrends

Usage:
    python3 test_google_trends.py
"""

import time
from pytrends.exceptions import TooManyRequestsError
from pytrends.request import TrendReq

# ── Config ────────────────────────────────────────────────────────────────────

COINS = [
    "bitcoin",
    "ethereum",
    "solana",
    "cardano",
    "chainlink",
]

# Timeframe options:
#   "now 1-d"    → last 24 hours (hourly resolution)
#   "now 7-d"    → last 7 days (hourly resolution)
#   "today 1-m"  → last 30 days (daily resolution)
#   "today 3-m"  → last 90 days (daily resolution)
#   "today 12-m" → last 12 months (weekly resolution)
TIMEFRAME = "today 1-m"

# Google Trends API only supports 5 keywords per request
BATCH_SIZE = 5


# ── Fetch ─────────────────────────────────────────────────────────────────────

def fetch_trends(keywords: list[str], timeframe: str) -> dict:
    """
    Returns a dict mapping each keyword to its interest-over-time data.

    Interest values are 0-100 (relative to peak in the window).
    100 = peak popularity, 0 = < 1% of peak.
    """
    pytrends = TrendReq(hl="en-US", tz=0)
    results = {}

    for i in range(0, len(keywords), BATCH_SIZE):
        batch = keywords[i : i + BATCH_SIZE]
        print(f"\nFetching trends for: {batch}")

        pytrends.build_payload(batch, timeframe=timeframe, geo="")

        try:
            df = pytrends.interest_over_time()
        except TooManyRequestsError:
            print("  Google rate limit hit (429). Sleeping 60s and retrying once...")
            time.sleep(60)
            try:
                df = pytrends.interest_over_time()
            except TooManyRequestsError:
                print("  Still rate-limited after retry. Google Trends may be blocking this IP.")
                print("  Try again in a few minutes or use a VPN/different network.")
                return results

        if df.empty:
            print("  No data returned for this batch.")
            continue

        # Drop the "isPartial" column if present
        if "isPartial" in df.columns:
            df = df.drop(columns=["isPartial"])

        for kw in batch:
            if kw in df.columns:
                series = df[kw]
                results[kw] = {
                    "timeframe": timeframe,
                    "latest_value": int(series.iloc[-1]),
                    "peak_value": int(series.max()),
                    "average_value": round(float(series.mean()), 2),
                    "datapoints": [
                        {"date": str(date.date()), "value": int(val)}
                        for date, val in series.items()
                    ],
                }
            else:
                results[kw] = None

        # Be polite — Google rate-limits aggressive requests
        if i + BATCH_SIZE < len(keywords):
            time.sleep(2)

    return results


def fetch_related_queries(keyword: str) -> dict:
    """
    Returns top and rising related queries for a single keyword.
    Useful for understanding what people are actually searching alongside the coin.
    """
    pytrends = TrendReq(hl="en-US", tz=0)
    pytrends.build_payload([keyword], timeframe=TIMEFRAME, geo="")
    related = pytrends.related_queries()

    result = {}
    if keyword in related:
        top = related[keyword].get("top")
        rising = related[keyword].get("rising")
        result["top"]    = top.head(5).to_dict("records") if top is not None else []
        result["rising"] = rising.head(5).to_dict("records") if rising is not None else []
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    print("=" * 60)
    print(f"Google Trends — Crypto Search Interest")
    print(f"Timeframe: {TIMEFRAME}")
    print("=" * 60)

    trends = fetch_trends(COINS, TIMEFRAME)

    print("\n── Summary ──────────────────────────────────────────────────")
    for coin, data in trends.items():
        if data:
            print(f"\n{coin.upper()}")
            print(f"  Latest value  : {data['latest_value']} / 100")
            print(f"  Peak value    : {data['peak_value']} / 100")
            print(f"  Average value : {data['average_value']} / 100")
            print(f"  Data points   : {len(data['datapoints'])}")
        else:
            print(f"\n{coin.upper()} — no data returned")

    # Show related queries for bitcoin as a sample
    print("\n── Related Queries for 'bitcoin' ────────────────────────────")
    related = fetch_related_queries("bitcoin")
    print("Top:")
    for q in related.get("top", []):
        print(f"  {q.get('query', '?'):30s}  value={q.get('value', '?')}")
    print("Rising:")
    for q in related.get("rising", []):
        print(f"  {q.get('query', '?'):30s}  value={q.get('value', '?')}")

    print("\n── Raw JSON output sample (bitcoin) ─────────────────────────")
    print(json.dumps(trends.get("bitcoin"), indent=2))
