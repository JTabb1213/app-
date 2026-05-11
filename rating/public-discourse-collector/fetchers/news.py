"""
fetchers/news.py
================
Fetches recent news headlines for a coin via NewsAPI and returns
an average VADER compound sentiment score (-1.0 to +1.0).

Requires a free NewsAPI key: https://newsapi.org
Set NEWSAPI_KEY in your .env file.
"""

import time
import requests
from datetime import datetime, timezone, timedelta
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

import config

_analyzer = SentimentIntensityAnalyzer()

_DATE_FROM = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_sentiment(coin: dict) -> dict:
    """
    Fetch news articles for a coin and return avg VADER compound sentiment.

    Returns:
        {
            "avg_compound": float | None,  # -1 to +1
            "article_count": int,
            "source": "newsapi",
        }
    """
    if not config.NEWSAPI_KEY:
        return {"avg_compound": None, "article_count": 0, "source": "newsapi", "error": "NEWSAPI_KEY not set"}

    queries   = coin.get("search_queries", [coin["name"]])
    endpoint  = f"{config.NEWSAPI_BASE_URL}/everything"
    seen_urls = set()
    all_scored = []

    for query in queries:
        params = {
            "q":        query,
            "from":     _DATE_FROM,
            "sortBy":   "publishedAt",
            "language": "en",
            "pageSize": 20,
            "apiKey":   config.NEWSAPI_KEY,
        }
        try:
            resp = requests.get(endpoint, params=params, timeout=10)
            if resp.status_code == 429:
                time.sleep(60)
                resp = requests.get(endpoint, params=params, timeout=10)
            resp.raise_for_status()
            articles = resp.json().get("articles", [])
        except Exception:
            continue

        for article in articles:
            url = article.get("url", "")
            if url in seen_urls:
                continue
            seen_urls.add(url)

            title = article.get("title") or ""
            desc  = article.get("description") or ""
            text  = f"{title}. {desc}".strip()
            if text:
                compound = _analyzer.polarity_scores(text)["compound"]
                all_scored.append(compound)

        time.sleep(0.5)

    if not all_scored:
        return {"avg_compound": None, "article_count": 0, "source": "newsapi"}

    avg = round(sum(all_scored) / len(all_scored), 4)
    return {
        "avg_compound":  avg,
        "article_count": len(all_scored),
        "source":        "newsapi",
    }
