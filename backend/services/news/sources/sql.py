"""
News service — SQL source
Table: news_cache
  coin_id     TEXT PRIMARY KEY
  articles    JSONB          -- array of {title, url, source, published_at}
  fetched_at  TIMESTAMPTZ
"""

import json
import logging
import os
from datetime import timezone
from typing import Optional

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

_conn = None


def _pg_connect():
    primary  = os.getenv("DATABASE_URL")
    fallback = os.getenv("DATABASE_URL_IPV4")
    try:
        return psycopg2.connect(primary, connect_timeout=5)
    except psycopg2.OperationalError as exc:
        if fallback and fallback != primary:
            logger.warning("[news/sql] Primary unreachable (%s), trying IPv4 fallback", exc)
            return psycopg2.connect(fallback, connect_timeout=5)
        raise


def _get_conn():
    global _conn
    try:
        if _conn is None or _conn.closed:
            raise psycopg2.OperationalError("no connection")
        _conn.cursor().execute("SELECT 1")
    except Exception:
        _conn = _pg_connect()
    return _conn


def get(coin_id: str) -> Optional[list]:
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT articles FROM news_cache WHERE coin_id = %s",
                (coin_id,),
            )
            row = cur.fetchone()
        if row and row["articles"]:
            articles = row["articles"]
            if isinstance(articles, str):
                articles = json.loads(articles)
            return articles
    except Exception as exc:
        logger.warning("[news/sql] Read failed for %s: %s", coin_id, exc)
    return None


def upsert(coin_id: str, articles: list) -> None:
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO news_cache (coin_id, articles, fetched_at)
                VALUES (%s, %s::jsonb, NOW())
                ON CONFLICT (coin_id) DO UPDATE
                    SET articles   = EXCLUDED.articles,
                        fetched_at = EXCLUDED.fetched_at
                """,
                (coin_id, json.dumps(articles)),
            )
        conn.commit()
    except Exception as exc:
        logger.warning("[news/sql] Upsert failed for %s: %s", coin_id, exc)
        try:
            _conn.rollback()
        except Exception:
            pass
