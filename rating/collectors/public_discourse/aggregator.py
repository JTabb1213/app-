"""
Public Discourse aggregator — combines Reddit, NewsAPI, and Google Trends
signals into a single result dict for one coin.

This is the only file that imports all three sources. It owns the shape
of the dict that gets written to the public_discourse SQL column.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from .sources import cache as disk_cache
from .sources import reddit
from .sources import news_sentiment
# from .sources import newsapi        # disabled until NEWSAPI_KEY is configured
# from .sources import serpapi_trends  # disabled until SERPAPI_KEY is configured

logger = logging.getLogger(__name__)


def fetch(coin: dict, newsapi_key: str = "", serpapi_key: str = "") -> Optional[dict]:
    """
    Fetch all discourse signals for a single coin and return a combined dict.

    Call serpapi_trends.prefetch_batch() from the orchestrator before the
    per-coin loop — that populates the trends cache so this function makes
    zero extra Trends API calls.

    Args:
        coin:        coin dict with at least "coin_id"; optionally "symbol",
                     "subreddits", "search_queries"
        newsapi_key: NewsAPI key (skips NewsAPI if empty)
        serpapi_key: SerpAPI key (used only for the single-coin fallback if
                     the cache is cold; normally pre-populated by prefetch_batch)

    Returns:
        dict ready to be stored in the public_discourse JSONB column, or None
        on a hard failure (though individual source failures return None fields,
        not None for the whole result).
    """
    coin_id = coin["coin_id"]
    logger.info(f"[Discourse] Fetching {coin_id}")

    if serpapi_key:
        os.environ.setdefault("SERPAPI_KEY", serpapi_key)

    cache = disk_cache.load(coin_id)

    reddit_compound, reddit_count = reddit.fetch(coin, cache)
    news_compound, news_count     = news_sentiment.fetch(coin, cache)
    #search_interest               = serpapi_trends.fetch(coin, cache, serpapi_key)

    disk_cache.save(coin_id, cache)

    return {
        "coin_id":             coin_id,
        "symbol":              coin.get("symbol", ""),
        "reddit_compound":     reddit_compound,
        "reddit_post_count":   reddit_count,
        "news_compound":       news_compound,
        "news_article_count":  news_count,
        #"search_interest":    search_interest,
        "snapshot_time":       datetime.now(timezone.utc).isoformat(),
    }
