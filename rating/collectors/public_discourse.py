"""
Collector: Public Discourse
============================
Pure data fetcher — no SQL, no Redis.
Returns social sentiment (Reddit + News) and search interest (Google Trends).

Returns dict or None on failure:
{
    coin_id, symbol,
    reddit_compound,    # VADER avg compound -1 to +1 (None if unavailable)
    reddit_post_count,
    news_compound,      # VADER avg compound -1 to +1 (None if unavailable)
    news_article_count,
    search_interest,    # Google Trends avg 0-100 (None if unavailable)
    snapshot_time,
    source
}
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger    = logging.getLogger(__name__)
_analyzer = SentimentIntensityAnalyzer()

NEWSAPI_BASE  = "https://newsapi.org/v2"
REDDIT_BASE   = "https://www.reddit.com"
TRENDS_DELAY  = 5   # seconds between Google Trends calls (avoid 429)


# ── Reddit ─────────────────────────────────────────────────────────────────────

def _fetch_reddit(coin: dict) -> tuple[float | None, int]:
    """
    Returns (avg_compound, post_count) using the public Reddit JSON API.
    No credentials needed.
    """
    subreddits = coin.get("subreddits", [])
    if not subreddits:
        return None, 0

    texts = []
    headers = {"User-Agent": "ccs-discourse-collector/1.0"}

    for sub in subreddits[:3]:   # cap to avoid too many requests
        url = f"{REDDIT_BASE}/r/{sub}/hot.json"
        try:
            resp = requests.get(url, params={"limit": 25}, headers=headers, timeout=10)
            if resp.status_code != 200:
                continue
            posts = resp.json().get("data", {}).get("children", [])
            for post in posts:
                title = post.get("data", {}).get("title", "")
                if title:
                    texts.append(title)
        except Exception as exc:
            logger.warning(f"[Reddit] {sub}: {exc}")

    if not texts:
        return None, 0

    compounds = [_analyzer.polarity_scores(t)["compound"] for t in texts]
    avg = round(sum(compounds) / len(compounds), 4)
    return avg, len(texts)


# ── News ───────────────────────────────────────────────────────────────────────

def _fetch_news(coin: dict, newsapi_key: str) -> tuple[float | None, int]:
    """
    Returns (avg_compound, article_count) from NewsAPI.
    Returns (None, 0) if no API key configured.
    """
    if not newsapi_key:
        return None, 0

    queries = coin.get("search_queries", [coin.get("symbol", coin["coin_id"])])
    query   = " OR ".join(f'"{q}"' for q in queries[:2])
    url     = f"{NEWSAPI_BASE}/everything"
    params  = {
        "q":        query,
        "language": "en",
        "pageSize": 20,
        "sortBy":   "publishedAt",
        "apiKey":   newsapi_key,
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return None, 0
        articles = resp.json().get("articles", [])
        if not articles:
            return None, 0
        texts     = [a.get("title", "") + " " + (a.get("description") or "") for a in articles]
        compounds = [_analyzer.polarity_scores(t)["compound"] for t in texts if t.strip()]
        avg       = round(sum(compounds) / len(compounds), 4) if compounds else None
        return avg, len(articles)
    except Exception as exc:
        logger.warning(f"[News] {coin['coin_id']}: {exc}")
        return None, 0


# ── Google Trends ──────────────────────────────────────────────────────────────

def _fetch_trends(coin: dict) -> float | None:
    """
    Returns avg Google Trends interest (0-100) or None on failure.
    Uses pytrends — free, no key needed.
    """
    try:
        from pytrends.request import TrendReq
        queries = coin.get("search_queries", [coin.get("symbol", coin["coin_id"])])
        kw      = queries[0]
        pt      = TrendReq(hl="en-US", tz=360)
        pt.build_payload([kw], timeframe="today 3-m")
        df = pt.interest_over_time()
        if df.empty or kw not in df.columns:
            return None
        avg = float(df[kw].mean())
        return round(avg, 2)
    except Exception as exc:
        logger.warning(f"[Trends] {coin['coin_id']}: {exc}")
        return None


# ── Main fetch ─────────────────────────────────────────────────────────────────

def fetch(coin: dict, newsapi_key: str = "") -> Optional[dict]:
    """
    Fetch all public discourse signals for a single coin.

    Args:
        coin:        dict with coin_id, symbol, subreddits, search_queries keys
        newsapi_key: NewsAPI key (optional)
    """
    coin_id = coin["coin_id"]
    logger.info(f"[Discourse] Fetching {coin_id}")

    reddit_compound, reddit_count   = _fetch_reddit(coin)
    news_compound,   news_count     = _fetch_news(coin, newsapi_key)
    time.sleep(TRENDS_DELAY)
    search_interest                 = _fetch_trends(coin)

    return {
        "coin_id":            coin_id,
        "symbol":             coin.get("symbol", ""),
        "reddit_compound":    reddit_compound,
        "reddit_post_count":  reddit_count,
        "news_compound":      news_compound,
        "news_article_count": news_count,
        "search_interest":    search_interest,
        "snapshot_time":      datetime.now(timezone.utc).isoformat(),
        "source":             "Reddit/NewsAPI/GoogleTrends",
    }
