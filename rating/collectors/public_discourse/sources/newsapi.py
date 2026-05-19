"""
NewsAPI source — fetches recent news headlines/descriptions for a coin and
returns a VADER compound sentiment score + article count.

Lookback window: 7 days.
Cache key: "news"   TTL: DISCOURSE_NEWS_TTL_HOURS (default 6 h)
"""

import logging
from datetime import datetime, timedelta, timezone

import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from . import cache as disk_cache

logger    = logging.getLogger(__name__)
_analyzer = SentimentIntensityAnalyzer()

_BASE = "https://newsapi.org/v2"


def fetch(coin: dict, newsapi_key: str, cache: dict) -> tuple[float | None, int]:
    """
    Return (compound_sentiment, article_count) for the coin's search queries.
    Reads from / writes to the shared in-memory cache dict.
    Falls back to the last stale value on rate-limit or API error.
    """
    if not newsapi_key:
        return None, 0

    hit = disk_cache.get(cache, "news")
    if hit is not disk_cache.MISS:
        return hit

    queries = coin.get("search_queries", [coin.get("symbol", coin["coin_id"])])
    query   = " OR ".join(f'"{q}"' for q in queries[:2])
    from_dt = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    params  = {
        "q": query, "language": "en", "pageSize": 20,
        "sortBy": "publishedAt", "from": from_dt, "apiKey": newsapi_key,
    }

    try:
        resp = requests.get(f"{_BASE}/everything", params=params, timeout=10)

        if resp.status_code in (429, 426):
            label = "RATE LIMIT" if resp.status_code == 429 else "UPGRADE REQUIRED"
            logger.error(f"[NewsAPI] {coin['coin_id']}: {label} — returning cached data.")
            stale = cache.get("news_value")
            return stale if stale is not None else (None, 0)

        if resp.status_code != 200:
            logger.warning(f"[NewsAPI] {coin['coin_id']}: HTTP {resp.status_code}")
            stale = cache.get("news_value")
            return stale if stale is not None else (None, 0)

        data = resp.json()
        if data.get("status") != "ok":
            logger.warning(f"[NewsAPI] {coin['coin_id']}: {data.get('message', 'unknown')}")
            stale = cache.get("news_value")
            return stale if stale is not None else (None, 0)

        articles = data.get("articles", [])
        if not articles:
            return None, 0

        texts     = [a.get("title", "") + " " + (a.get("description") or "") for a in articles]
        compounds = [_analyzer.polarity_scores(t)["compound"] for t in texts if t.strip()]
        avg       = round(sum(compounds) / len(compounds), 4) if compounds else None
        result    = (avg, len(articles))
        disk_cache.put(cache, "news", result)
        return result

    except Exception as exc:
        logger.warning(f"[NewsAPI] {coin['coin_id']}: {exc}. Returning cached data.")
        stale = cache.get("news_value")
        return stale if stale is not None else (None, 0)
