"""
fetchers/reddit.py
==================
Fetches recent Reddit posts for a coin across its subreddits and returns
an average VADER compound sentiment score (-1.0 to +1.0).

No API key required — uses Reddit's public JSON API.
"""

import time
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

import config

HEADERS = {"User-Agent": "ccs-public-discourse-collector/1.0"}
_analyzer = SentimentIntensityAnalyzer()


def _fetch_posts(subreddit: str, query: str) -> list[dict]:
    url = f"{config.REDDIT_API_BASE_URL}/r/{subreddit}/search.json"
    params = {
        "q": query,
        "restrict_sr": "true",
        "sort": "new",
        "t": config.REDDIT_TIME_FILTER,
        "limit": config.REDDIT_POSTS_PER_SUB,
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        children = resp.json().get("data", {}).get("children", [])
        return [c["data"] for c in children]
    except Exception as e:
        return []


def fetch_sentiment(coin: dict) -> dict:
    """
    Fetch Reddit posts for a coin across all configured subreddits.
    Returns a dict with avg_compound (-1 to +1) and post_count.

    compound > 0   → net positive community sentiment
    compound < 0   → net negative
    compound ≈ 0   → neutral / mixed
    """
    query      = coin["search_queries"][0]
    subreddits = coin.get("subreddits", ["CryptoCurrency"])

    all_posts = []
    for sub in subreddits:
        posts = _fetch_posts(sub, query)
        all_posts.extend(posts)
        time.sleep(1)  # stay within ~1 req/s Reddit limit

    if not all_posts:
        return {"avg_compound": None, "post_count": 0, "source": "reddit"}

    compounds = []
    for post in all_posts:
        text = f"{post.get('title', '')}. {post.get('selftext', '')}".strip()
        if text:
            score = _analyzer.polarity_scores(text)["compound"]
            compounds.append(score)

    avg = round(sum(compounds) / len(compounds), 4) if compounds else None
    return {
        "avg_compound": avg,
        "post_count":   len(all_posts),
        "source":       "reddit",
    }
