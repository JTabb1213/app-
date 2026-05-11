"""
test_reddit_sentiment.py
========================
Fetches recent Reddit posts mentioning a crypto coin and scores each post
using VADER sentiment analysis (no ML model download required).

No API key needed — uses Reddit's public JSON API directly.
VADER runs locally with no external calls.

Install:
    pip install requests vaderSentiment

Usage:
    python3 test_reddit_sentiment.py
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

# ── Config ────────────────────────────────────────────────────────────────────

REDDIT_API_BASE_URL = os.getenv("REDDIT_API_BASE_URL", "https://www.reddit.com")

COINS = [
    {"coin_id": "bitcoin",   "query": "bitcoin",   "subreddits": ["Bitcoin", "CryptoCurrency"]},
    {"coin_id": "ethereum",  "query": "ethereum",  "subreddits": ["ethereum", "CryptoCurrency"]},
    {"coin_id": "solana",    "query": "solana",    "subreddits": ["solana", "CryptoCurrency"]},
    {"coin_id": "chainlink", "query": "chainlink", "subreddits": ["Chainlink", "CryptoCurrency"]},
]

POSTS_PER_SUBREDDIT = 25   # Reddit allows up to 100 per request (free)
TIME_FILTER = "week"       # "hour" | "day" | "week" | "month" | "year" | "all"

HEADERS = {"User-Agent": "crypto-sentiment-test/1.0"}

# ── Reddit fetch ──────────────────────────────────────────────────────────────

def fetch_subreddit_posts(subreddit: str, query: str, limit: int = 25, time_filter: str = "week") -> list[dict]:
    """
    Search a subreddit for posts containing the query string.
    Uses Reddit's public JSON search endpoint (no auth needed).
    """
    url = f"{REDDIT_API_BASE_URL}/r/{subreddit}/search.json"
    params = {
        "q": query,
        "restrict_sr": "true",
        "sort": "new",
        "t": time_filter,
        "limit": limit,
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        posts = data.get("data", {}).get("children", [])
        return [p["data"] for p in posts]
    except Exception as e:
        print(f"  Reddit fetch error ({subreddit}): {e}")
        return []


# ── Sentiment scoring ─────────────────────────────────────────────────────────

analyzer = SentimentIntensityAnalyzer()

def score_text(text: str) -> dict:
    """
    Returns VADER sentiment scores for a piece of text.
    compound: -1.0 (very negative) to +1.0 (very positive)
    pos/neu/neg: proportional scores (sum to 1.0)
    """
    return analyzer.polarity_scores(text)


def label(compound: float) -> str:
    if compound >= 0.05:
        return "positive"
    elif compound <= -0.05:
        return "negative"
    return "neutral"


# ── Aggregate ─────────────────────────────────────────────────────────────────

def analyse_coin(coin: dict) -> dict:
    coin_id   = coin["coin_id"]
    query     = coin["query"]
    subs      = coin["subreddits"]

    all_posts = []
    for sub in subs:
        print(f"  Fetching r/{sub} for '{query}'…")
        posts = fetch_subreddit_posts(sub, query, POSTS_PER_SUBREDDIT, TIME_FILTER)
        print(f"    → {len(posts)} posts")
        all_posts.extend(posts)
        time.sleep(1)  # stay within Reddit rate limit (~1 req/s)

    if not all_posts:
        return {"coin_id": coin_id, "error": "no posts found"}

    scored = []
    for post in all_posts:
        title = post.get("title", "")
        body  = post.get("selftext", "")
        text  = f"{title}. {body}".strip()

        scores = score_text(text)
        scored.append({
            "title":     title[:80],
            "subreddit": post.get("subreddit"),
            "score":     post.get("score", 0),          # Reddit upvotes
            "upvote_ratio": post.get("upvote_ratio"),
            "created":   datetime.fromtimestamp(
                             post.get("created_utc", 0), tz=timezone.utc
                         ).strftime("%Y-%m-%d"),
            "compound":  scores["compound"],
            "pos":       scores["pos"],
            "neg":       scores["neg"],
            "neu":       scores["neu"],
            "sentiment": label(scores["compound"]),
        })

    compounds = [p["compound"] for p in scored]
    avg_compound = round(sum(compounds) / len(compounds), 4)

    counts = {"positive": 0, "negative": 0, "neutral": 0}
    for p in scored:
        counts[p["sentiment"]] += 1

    return {
        "coin_id":        coin_id,
        "query":          query,
        "timeframe":      TIME_FILTER,
        "post_count":     len(scored),
        "avg_compound":   avg_compound,
        "overall_label":  label(avg_compound),
        "breakdown":      counts,
        "posts":          sorted(scored, key=lambda x: abs(x["compound"]), reverse=True)[:10],
    }


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    print("=" * 60)
    print("Reddit Sentiment Analysis — Crypto")
    print(f"Timeframe: {TIME_FILTER}  |  Posts per subreddit: {POSTS_PER_SUBREDDIT}")
    print("=" * 60)

    results = []
    for coin in COINS:
        print(f"\n── {coin['coin_id'].upper()} ──────────────────────────────────────────")
        result = analyse_coin(coin)
        results.append(result)

        if "error" not in result:
            print(f"  Posts analysed  : {result['post_count']}")
            print(f"  Avg compound    : {result['avg_compound']:+.4f}")
            print(f"  Overall label   : {result['overall_label'].upper()}")
            print(f"  Breakdown       : {result['breakdown']}")
            print(f"\n  Top 3 most opinionated posts:")
            for p in result["posts"][:3]:
                print(f"    [{p['sentiment']:8s}  {p['compound']:+.3f}]  {p['title']}")
        else:
            print(f"  Error: {result['error']}")

    print("\n\n── Full JSON output (ethereum) ──────────────────────────────")
    eth = next((r for r in results if r["coin_id"] == "ethereum"), None)
    if eth:
        eth_summary = {k: v for k, v in eth.items() if k != "posts"}
        print(json.dumps(eth_summary, indent=2))
