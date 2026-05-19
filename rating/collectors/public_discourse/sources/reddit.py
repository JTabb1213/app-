"""
Reddit source — fetches hot post titles from a coin's subreddits and
returns a VADER compound sentiment score + post count.

Cache key: "reddit"   TTL: DISCOURSE_REDDIT_TTL_HOURS (default 2 h)
"""

import logging

import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from . import cache as disk_cache

logger    = logging.getLogger(__name__)
_analyzer = SentimentIntensityAnalyzer()

_BASE    = "https://www.reddit.com"
_HEADERS = {"User-Agent": "ccs-discourse-collector/1.0"}


def fetch(coin: dict, cache: dict) -> tuple[float | None, int]:
    """
    Return (compound_sentiment, post_count) for the coin's subreddits.
    Reads from / writes to the shared in-memory cache dict.
    Falls back to the last stale value on API failure.
    """
    hit = disk_cache.get(cache, "reddit")
    if hit is not disk_cache.MISS:
        return hit

    subreddits = coin.get("subreddits", [])
    if not subreddits:
        return None, 0

    texts = []
    try:
        for sub in subreddits[:3]:
            resp = requests.get(
                f"{_BASE}/r/{sub}/hot.json",
                params={"limit": 25}, headers=_HEADERS, timeout=10,
            )
            if resp.status_code == 429:
                logger.warning(f"[Reddit] {coin['coin_id']}: 429 on r/{sub}")
                break
            if resp.status_code != 200:
                logger.warning(f"[Reddit] {coin['coin_id']}: HTTP {resp.status_code} on r/{sub}")
                continue
            for post in resp.json().get("data", {}).get("children", []):
                title = post.get("data", {}).get("title", "")
                if title:
                    texts.append(title)
    except Exception as exc:
        logger.warning(f"[Reddit] {coin['coin_id']}: {exc}")

    if not texts:
        stale = cache.get("reddit_value")
        return stale if stale is not None else (None, 0)

    compounds = [_analyzer.polarity_scores(t)["compound"] for t in texts]
    result    = (round(sum(compounds) / len(compounds), 4), len(texts))
    disk_cache.put(cache, "reddit", result)
    return result
