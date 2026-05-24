"""
Public Discourse — news sentiment source
=========================================
Reads pre-computed news sentiment snapshots from the
news_sentiment_snapshots SQL table (written by the news-sentiment-collector
service every ~4 hours).

Returns the average VADER compound score across all buckets in the last
LOOKBACK_DAYS days, and the total article count over that window.
"""

import logging
import os

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

_DATABASE_URL = os.getenv("DATABASE_URL", "")
_LOOKBACK_DAYS = int(os.getenv("NEWS_SENTIMENT_LOOKBACK_DAYS", "7"))

_pg = None


def _get_pg():
    global _pg
    try:
        if _pg is None or _pg.closed:
            raise psycopg2.OperationalError
        _pg.cursor().execute("SELECT 1")
    except Exception:
        _pg = psycopg2.connect(_DATABASE_URL, connect_timeout=10)
    return _pg


def fetch(coin: dict, _cache: dict) -> tuple[float | None, int]:
    """
    Return (avg_compound_score, total_article_count) for the coin over the
    last LOOKBACK_DAYS days.

    avg_compound_score is in [-1, 1] (VADER compound scale).
    Returns (None, 0) if no snapshots exist yet.
    """
    coin_id = coin["coin_id"]
    try:
        conn = _get_pg()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT AVG(avg_score)     AS avg_compound,
                       SUM(article_count) AS total_articles
                FROM news_sentiment_snapshots
                WHERE coin_id    = %s
                  AND bucket_start >= NOW() - INTERVAL '%s days'
                """,
                (coin_id, _LOOKBACK_DAYS),
            )
            row = cur.fetchone()

        if row and row["avg_compound"] is not None:
            compound = round(float(row["avg_compound"]), 6)
            count    = int(row["total_articles"] or 0)
            logger.debug("[news_sentiment] %s → compound=%.3f, articles=%d", coin_id, compound, count)
            return compound, count

        logger.debug("[news_sentiment] %s — no snapshots in last %d days", coin_id, _LOOKBACK_DAYS)
        return None, 0

    except Exception as exc:
        logger.warning("[news_sentiment] %s fetch failed: %s", coin_id, exc)
        return None, 0
