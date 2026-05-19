"""
News service
============
Resolution order:
  1. Redis  (crypto:news:{coin_id}, 1h TTL)
  2. Postgres  (news_cache table)
  3. Google News RSS live fetch → cache in Redis + Postgres

Returns a list of article dicts or None.
"""

import logging

from .sources import redis_source, sql, google_rss

logger = logging.getLogger(__name__)


def get_news(coin_id: str) -> list | None:
    # 1 — Redis
    articles = redis_source.get(coin_id)
    if articles:
        logger.info("[news] %s served from Redis", coin_id)
        return articles

    # 2 — Postgres
    articles = sql.get(coin_id)
    if articles:
        logger.info("[news] %s served from SQL", coin_id)
        redis_source.set(coin_id, articles)
        return articles

    # 3 — Google News RSS
    logger.info("[news] %s not cached, fetching from Google News", coin_id)
    articles = google_rss.fetch(coin_id)
    if not articles:
        logger.warning("[news] No articles found for %s", coin_id)
        return None

    redis_source.set(coin_id, articles)
    sql.upsert(coin_id, articles)

    return articles
