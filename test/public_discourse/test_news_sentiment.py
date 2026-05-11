"""
test_news_sentiment.py
======================
Fetches recent crypto news articles via NewsAPI and scores each headline
+ description using VADER sentiment analysis.

Requires a FREE NewsAPI key — sign up at https://newsapi.org (no credit card).
Free tier: 100 requests/day, articles from the past 30 days.

Install:
    pip install requests vaderSentiment

Usage:
    NEWSAPI_KEY=your_key_here python3 test_news_sentiment.py
    -- OR --
    Set NEWSAPI_KEY in your .env and run:
    python3 test_news_sentiment.py
"""

import os
import time
import requests
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# ── Env loading ─────────────────────────────────────────────────────────────────
root_env = Path(__file__).resolve().parents[2] / ".env"
if root_env.exists():
    load_dotenv(root_env, override=False)

# ── Config ─────────────────────────────────────────────────────────────────────

# Load from env or paste your key here for testing
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
NEWSAPI_BASE_URL = os.getenv("NEWSAPI_BASE_URL", "https://newsapi.org/v2")
NEWSAPI_ENDPOINT = f"{NEWSAPI_BASE_URL}/everything"

COINS = [
    {"coin_id": "bitcoin",   "queries": ["bitcoin", "BTC"]},
    {"coin_id": "ethereum",  "queries": ["ethereum", "ETH"]},
    {"coin_id": "solana",    "queries": ["solana", "SOL"]},
    {"coin_id": "chainlink", "queries": ["chainlink", "LINK token"]},
]

ARTICLES_PER_QUERY = 20  # free tier max is 100/request

# How far back to look (ISO 8601 date string, last 7 days)
# How far back to look (ISO 8601 date string, last 7 days)
from datetime import timedelta
DATE_FROM = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

# ── Fetch ─────────────────────────────────────────────────────────────────────

def fetch_articles(query: str, from_date: str, page_size: int = 20) -> list[dict]:
    """
    Search NewsAPI for articles matching the query string.
    Returns a list of article dicts.
    """
    if not NEWSAPI_KEY:
        raise RuntimeError(
            "NEWSAPI_KEY not set. Get a free key at https://newsapi.org "
            "and set it: export NEWSAPI_KEY=your_key"
        )

    params = {
        "q":        query,
        "from":     from_date,
        "sortBy":   "publishedAt",
        "language": "en",
        "pageSize": page_size,
        "apiKey":   NEWSAPI_KEY,
    }
    resp = requests.get(NEWSAPI_ENDPOINT, params=params, timeout=10)

    if resp.status_code == 401:
        raise RuntimeError("Invalid NewsAPI key.")
    if resp.status_code == 429:
        print("  Rate limit hit — sleeping 60s")
        time.sleep(60)
        resp = requests.get(NEWSAPI_ENDPOINT, params=params, timeout=10)

    resp.raise_for_status()
    data = resp.json()
    return data.get("articles", [])


# ── Sentiment scoring ─────────────────────────────────────────────────────────

analyzer = SentimentIntensityAnalyzer()

def score_article(article: dict) -> dict:
    """
    Score an article using its title + description.
    Returns the article enriched with sentiment fields.
    """
    title = article.get("title") or ""
    desc  = article.get("description") or ""
    text  = f"{title}. {desc}".strip()

    scores = analyzer.polarity_scores(text)
    compound = scores["compound"]

    if compound >= 0.05:
        sentiment = "positive"
    elif compound <= -0.05:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return {
        "title":     title[:100],
        "source":    article.get("source", {}).get("name"),
        "published": article.get("publishedAt", "")[:10],
        "url":       article.get("url"),
        "compound":  round(compound, 4),
        "pos":       round(scores["pos"], 4),
        "neg":       round(scores["neg"], 4),
        "neu":       round(scores["neu"], 4),
        "sentiment": sentiment,
    }


# ── Aggregate ─────────────────────────────────────────────────────────────────

def analyse_coin(coin: dict) -> dict:
    coin_id = coin["coin_id"]
    queries = coin["queries"]
    seen_urls = set()
    all_scored = []

    for query in queries:
        print(f"  Fetching news for '{query}'…")
        try:
            articles = fetch_articles(query, DATE_FROM, ARTICLES_PER_QUERY)
        except RuntimeError as e:
            return {"coin_id": coin_id, "error": str(e)}

        print(f"    → {len(articles)} articles")

        for article in articles:
            url = article.get("url", "")
            if url in seen_urls:
                continue  # deduplicate across queries
            seen_urls.add(url)
            scored = score_article(article)
            all_scored.append(scored)

        time.sleep(0.5)  # stay within free tier

    if not all_scored:
        return {"coin_id": coin_id, "error": "no articles found"}

    compounds = [a["compound"] for a in all_scored]
    avg_compound = round(sum(compounds) / len(compounds), 4)

    counts = {"positive": 0, "negative": 0, "neutral": 0}
    for a in all_scored:
        counts[a["sentiment"]] += 1

    if avg_compound >= 0.05:
        overall = "positive"
    elif avg_compound <= -0.05:
        overall = "negative"
    else:
        overall = "neutral"

    return {
        "coin_id":       coin_id,
        "from_date":     DATE_FROM[:10],
        "article_count": len(all_scored),
        "avg_compound":  avg_compound,
        "overall_label": overall,
        "breakdown":     counts,
        "articles":      sorted(all_scored, key=lambda x: abs(x["compound"]), reverse=True),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    if not NEWSAPI_KEY:
        print("ERROR: NEWSAPI_KEY is not set.")
        print("Get a free key at https://newsapi.org and run:")
        print("  export NEWSAPI_KEY=your_key_here")
        exit(1)

    print("=" * 60)
    print("NewsAPI Sentiment Analysis — Crypto")
    print(f"Articles from: {DATE_FROM[:10]} to today")
    print("=" * 60)

    results = []
    for coin in COINS:
        print(f"\n── {coin['coin_id'].upper()} ──────────────────────────────────────────")
        result = analyse_coin(coin)
        results.append(result)

        if "error" not in result:
            print(f"  Articles analysed : {result['article_count']}")
            print(f"  Avg compound      : {result['avg_compound']:+.4f}")
            print(f"  Overall label     : {result['overall_label'].upper()}")
            print(f"  Breakdown         : {result['breakdown']}")
            print(f"\n  Top 5 most opinionated headlines:")
            for a in result["articles"][:5]:
                print(f"    [{a['sentiment']:8s}  {a['compound']:+.4f}]  {a['title']}")
        else:
            print(f"  Error: {result['error']}")

    print("\n── Full JSON output (bitcoin) ───────────────────────────────")
    btc = next((r for r in results if r["coin_id"] == "bitcoin"), None)
    if btc:
        btc_summary = {k: v for k, v in btc.items() if k != "articles"}
        btc_summary["top_5_articles"] = btc.get("articles", [])[:5]
        print(json.dumps(btc_summary, indent=2))
