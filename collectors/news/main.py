"""
News Collector
==============
Runs on a fixed timer (default every 2 hours).
On each cycle:
  1. Load all tracked coin_ids from the rating_scores table.
  2. Fetch the latest news articles from Google News RSS for each coin.
  3. Upsert each result to:
       - PostgreSQL  →  news_cache table
       - Redis       →  crypto:news:{coin_id}  (TTL = REDIS_TTL)

This pre-populates the cache so users always get fast news on the CoinPage,
without waiting for a live RSS fetch on every page load.
"""

import json
import logging
import time
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

import psycopg2
import psycopg2.extras
import redis
import requests

import config

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("news-collector")

# ── DB / Redis connections ────────────────────────────────────────────────────

_pg  = None
_rdb = None


def _get_pg():
    global _pg
    try:
        if _pg is None or _pg.closed:
            raise psycopg2.OperationalError("no conn")
        _pg.cursor().execute("SELECT 1")
    except Exception:
        _pg = psycopg2.connect(config.DATABASE_URL, connect_timeout=10)
        logger.info("[DB] Connected to PostgreSQL")
    return _pg


def _get_redis():
    global _rdb
    if _rdb is None:
        _rdb = redis.from_url(config.REDIS_URL, decode_responses=True)
        logger.info("[Redis] Connected")
    return _rdb


# ── Load tracked coins ────────────────────────────────────────────────────────

def load_coin_ids() -> list[str]:
    try:
        conn = _get_pg()
        with conn.cursor() as cur:
            cur.execute("SELECT coin_id FROM rating_scores ORDER BY coin_id")
            rows = cur.fetchall()
        ids = [r[0] for r in rows]
        logger.info("[DB] Loaded %d tracked coins", len(ids))
        return ids
    except Exception as exc:
        logger.error("[DB] load_coin_ids failed: %s", exc)
        return []


# ── Google News RSS fetch ─────────────────────────────────────────────────────

_TIMEOUT = 12


def _coin_name(coin_id: str) -> str:
    return coin_id.replace("-", " ")


def fetch_news(coin_id: str) -> list | None:
    query = quote_plus(f"{_coin_name(coin_id)} crypto")
    url   = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    try:
        resp = requests.get(
            url, timeout=_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (compatible; news-collector/1.0)"},
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("[%s] RSS fetch failed: %s", coin_id, exc)
        return None

    try:
        root  = ET.fromstring(resp.content)
        items = root.findall(".//item")
        articles = []
        for item in items[: config.MAX_ARTICLES]:
            source_el = item.find("source")
            articles.append({
                "title":        (item.findtext("title", "") or "").strip(),
                "url":          (item.findtext("link",  "") or "").strip(),
                "source":       source_el.text.strip() if source_el is not None else "Google News",
                "published_at": (item.findtext("pubDate", "") or "").strip(),
            })
        return articles if articles else None
    except ET.ParseError as exc:
        logger.warning("[%s] XML parse error: %s", coin_id, exc)
        return None


# ── Upsert SQL ────────────────────────────────────────────────────────────────

def upsert_sql(coin_id: str, articles: list) -> bool:
    try:
        conn = _get_pg()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO news_cache (coin_id, articles, fetched_at)
                VALUES (%s, %s::jsonb, NOW())
                ON CONFLICT (coin_id) DO UPDATE SET
                    articles   = EXCLUDED.articles,
                    fetched_at = NOW()
                """,
                (coin_id, json.dumps(articles)),
            )
        conn.commit()
        return True
    except Exception as exc:
        logger.error("[DB] upsert news failed for %s: %s", coin_id, exc)
        try:
            _get_pg().rollback()
        except Exception:
            pass
        return False


# ── Write Redis ───────────────────────────────────────────────────────────────

def write_redis(coin_id: str, articles: list) -> bool:
    try:
        _get_redis().setex(
            f"crypto:news:{coin_id}",
            config.REDIS_TTL,
            json.dumps(articles),
        )
        return True
    except Exception as exc:
        logger.warning("[Redis] write news failed for %s: %s", coin_id, exc)
        return False


# ── Check news_cache schema ───────────────────────────────────────────────────

def _ensure_news_cache_schema():
    """Ensure the news_cache table has a coin_id UNIQUE constraint for ON CONFLICT."""
    try:
        conn = _get_pg()
        with conn.cursor() as cur:
            # Check if the table has a unique/primary key on coin_id
            cur.execute(
                """
                SELECT COUNT(*) FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage ccu
                    ON tc.constraint_name = ccu.constraint_name
                WHERE tc.table_name = 'news_cache'
                  AND ccu.column_name = 'coin_id'
                  AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
                """
            )
            if cur.fetchone()[0] == 0:
                logger.warning("[DB] news_cache has no UNIQUE on coin_id — adding one")
                cur.execute(
                    "ALTER TABLE news_cache ADD COLUMN IF NOT EXISTS coin_id_key TEXT UNIQUE"
                )
        conn.commit()
    except Exception as exc:
        logger.warning("[DB] Schema check skipped: %s", exc)


# ── Main cycle ────────────────────────────────────────────────────────────────

def run_once():
    logger.info("═" * 55)
    logger.info("News collector cycle starting")
    coin_ids = load_coin_ids()
    if not coin_ids:
        logger.warning("No tracked coins found — skipping cycle")
        return

    ok = fail = 0
    for coin_id in coin_ids:
        articles = fetch_news(coin_id)
        if not articles:
            logger.warning("[%s] No articles — skipping", coin_id)
            fail += 1
        else:
            sql_ok   = upsert_sql(coin_id, articles)
            redis_ok = write_redis(coin_id, articles)
            if sql_ok:
                ok += 1
                logger.debug("[%s] ✓ %d articles saved (redis=%s)", coin_id, len(articles), redis_ok)
            else:
                fail += 1

        time.sleep(config.REQUEST_DELAY)

    logger.info("News cycle complete — ok=%d  fail=%d", ok, fail)


def main():
    logger.info("News Collector starting (interval=%ds)", config.RUN_INTERVAL)
    while True:
        try:
            run_once()
        except Exception as exc:
            logger.exception("Unhandled error in run_once: %s", exc)
        logger.info("Sleeping %d s until next cycle", config.RUN_INTERVAL)
        time.sleep(config.RUN_INTERVAL)


if __name__ == "__main__":
    main()
