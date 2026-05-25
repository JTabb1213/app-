"""
News Sentiment Collector
========================
Runs on a fixed timer (default every 4 hours).

On each cycle, for every coin in coin_aliases.json:
  1. Fetch up to MAX_ARTICLES headlines from Google News RSS using the
     coin's canonical name as the search query (e.g. "bitcoin crypto").
  2. Keep only articles whose headline contains at least one of the coin's
     aliases as a whole word (case-insensitive).  This filters out articles
     that happened to include the query string but aren't really about the coin.
  3. Run VADER sentiment on each headline → compound score in [-1, 1].
  4. Compute the average compound score for the bucket.
  5. Write one row to news_sentiment_snapshots with:
       coin_id, bucket_start, avg_score, article_count, articles {url: score}

The "bucket_start" is floored to the nearest RUN_INTERVAL boundary so that
repeated runs in the same window update the same row (upsert).

The rating score-orchestrator reads the most recent ~7 days of buckets and
uses the average as the news_compound input for the public discourse score.
"""

import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import quote_plus

import psycopg2
import psycopg2.extras
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

import config

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("news-sentiment-collector")

_analyzer = SentimentIntensityAnalyzer()

# ── DB connection ─────────────────────────────────────────────────────────────

_pg = None


def _get_pg():
    global _pg
    try:
        if _pg is None or _pg.closed:
            raise psycopg2.OperationalError
        _pg.cursor().execute("SELECT 1")
    except Exception:
        _pg = psycopg2.connect(config.DATABASE_URL, connect_timeout=10)
        _pg.autocommit = False
        logger.info("[DB] Connected to PostgreSQL")
    return _pg


# ── Alias loading ─────────────────────────────────────────────────────────────

def load_coins() -> list[dict]:
    """
    Return a list of dicts:
      { coin_id, symbol, aliases, search_query }
    """
    try:
        with open(config.COIN_ALIASES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        logger.error("[aliases] Failed to load %s: %s", config.COIN_ALIASES_PATH, exc)
        return []

    coins = []
    for coin_id, info in data.get("assets", {}).items():
        aliases = [a.lower() for a in info.get("aliases", [coin_id])]
        coins.append({
            "coin_id":      coin_id,
            "symbol":       info.get("symbol", ""),
            "aliases":      aliases,
            # Search query: canonical alias + "crypto" to focus results
            "search_query": f"{aliases[0]} crypto",
        })
    logger.info("[aliases] Loaded %d coins", len(coins))
    return coins


# ── RSS fetch ─────────────────────────────────────────────────────────────────

_RSS_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; news-sentiment/1.0)"}
_TIMEOUT     = 12


def _fetch_rss(search_query: str) -> list[dict]:
    """Fetch items from Google News RSS. Returns list of {title, url, published}."""
    url = (
        f"{config.GOOGLE_NEWS_RSS_BASE_URL}"
        f"?q={quote_plus(search_query)}&hl=en-US&gl=US&ceid=US:en"
    )
    try:
        resp = requests.get(url, timeout=_TIMEOUT, headers=_RSS_HEADERS)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("[RSS] Fetch failed for '%s': %s", search_query, exc)
        return []

    try:
        root  = ET.fromstring(resp.content)
        items = root.findall(".//item")
        results = []
        for item in items[:config.MAX_ARTICLES]:
            title = (item.findtext("title") or "").strip()
            link  = (item.findtext("link") or "").strip()
            pub   = (item.findtext("pubDate") or "").strip()
            if title and link:
                results.append({"title": title, "url": link, "published": pub})
        return results
    except ET.ParseError as exc:
        logger.warning("[RSS] XML parse error for '%s': %s", search_query, exc)
        return []


# ── Alias headline filter ─────────────────────────────────────────────────────

def _headline_matches(title: str, aliases: list[str]) -> bool:
    """
    Return True if the headline contains at least one alias as a whole word.
    Short aliases (≤3 chars, e.g. "op", "uni", "bat") require the symbol form
    (uppercase) to reduce false positives — we check them against the raw title.
    """
    title_lower = title.lower()
    for alias in aliases:
        if len(alias) <= 3:
            # For short tickers, do a case-sensitive whole-word match on the
            # original title to avoid matching common English words.
            if re.search(r'\b' + re.escape(alias.upper()) + r'\b', title):
                return True
        else:
            if re.search(r'\b' + re.escape(alias) + r'\b', title_lower):
                return True
    return False


# ── Sentiment scoring ─────────────────────────────────────────────────────────

def _score_headline(title: str) -> float:
    return _analyzer.polarity_scores(title)["compound"]


# ── Bucket helpers ────────────────────────────────────────────────────────────

def _current_bucket() -> datetime:
    """Floor current UTC time to the nearest RUN_INTERVAL boundary."""
    now_ts = int(datetime.now(timezone.utc).timestamp())
    bucket_ts = (now_ts // config.RUN_INTERVAL) * config.RUN_INTERVAL
    return datetime.fromtimestamp(bucket_ts, tz=timezone.utc)


# ── SQL dedup ─────────────────────────────────────────────────────────────────

def _get_seen_urls(coin_id: str, lookback_buckets: int = 3) -> set[str]:
    """
    Return the set of article URLs already stored for this coin in the last
    `lookback_buckets` buckets.  Articles appearing in the RSS feed again
    within that window are skipped so we don't double-count them.
    """
    try:
        conn = _get_pg()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT articles
                FROM news_sentiment_snapshots
                WHERE coin_id = %s
                ORDER BY bucket_start DESC
                LIMIT %s
                """,
                (coin_id, lookback_buckets),
            )
            rows = cur.fetchall()
        seen = set()
        for (articles_json,) in rows:
            if not articles_json:
                continue
            data = articles_json if isinstance(articles_json, dict) else json.loads(articles_json)
            seen.update(data.keys())
        return seen
    except Exception as exc:
        logger.warning("[DB] _get_seen_urls failed for %s: %s", coin_id, exc)
        return set()


# ── SQL upsert ────────────────────────────────────────────────────────────────

def _upsert(coin_id: str, bucket_start: datetime, article_scores: dict):
    if not article_scores:
        return
    avg_score = sum(article_scores.values()) / len(article_scores)
    conn = _get_pg()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO news_sentiment_snapshots
                    (coin_id, bucket_start, avg_score, article_count, articles)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (coin_id, bucket_start) DO UPDATE SET
                    avg_score     = EXCLUDED.avg_score,
                    article_count = EXCLUDED.article_count,
                    articles      = EXCLUDED.articles,
                    created_at    = NOW()
                """,
                (
                    coin_id,
                    bucket_start,
                    round(avg_score, 6),
                    len(article_scores),
                    json.dumps(article_scores),
                ),
            )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.error("[DB] Upsert failed for %s: %s", coin_id, exc)


# ── Main collection cycle ─────────────────────────────────────────────────────

def run_cycle(coins: list[dict], bucket_start: datetime):
    logger.info("=== Cycle start — bucket %s — %d coins ===", bucket_start.isoformat(), len(coins))
    success, skipped = 0, 0

    for coin in coins:
        coin_id = coin["coin_id"]
        try:
            items = _fetch_rss(coin["search_query"])
            if not items:
                skipped += 1
                continue

            article_scores = {}
            seen_urls = _get_seen_urls(coin_id)
            for item in items:
                url   = item["url"]
                title = item["title"]
                if url in seen_urls:
                    logger.debug("[%s] Skipping already-seen article: %s", coin_id, url)
                    continue
                if not _headline_matches(title, coin["aliases"]):
                    continue
                score = _score_headline(title)
                article_scores[url] = round(score, 6)

            if article_scores:
                _upsert(coin_id, bucket_start, article_scores)
                logger.info(
                    "[%s] %d articles → avg %.3f",
                    coin_id, len(article_scores),
                    sum(article_scores.values()) / len(article_scores),
                )
                success += 1
            else:
                logger.debug("[%s] 0 alias-matched headlines", coin_id)
                skipped += 1

        except Exception as exc:
            logger.error("[%s] Unexpected error: %s", coin_id, exc)
            skipped += 1

        time.sleep(config.REQUEST_DELAY)

    logger.info("=== Cycle done — %d written, %d skipped ===", success, skipped)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    logger.info("News Sentiment Collector starting (interval: %ds)", config.RUN_INTERVAL)
    # Ensure table exists
    try:
        conn = _get_pg()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS news_sentiment_snapshots (
                    coin_id       TEXT        NOT NULL,
                    bucket_start  TIMESTAMPTZ NOT NULL,
                    avg_score     FLOAT,
                    article_count INT         NOT NULL DEFAULT 0,
                    articles      JSONB,
                    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (coin_id, bucket_start)
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_nss_coin_bucket
                ON news_sentiment_snapshots (coin_id, bucket_start DESC)
            """)
        conn.commit()
        logger.info("[DB] Table ready")
    except Exception as exc:
        logger.error("[DB] Schema init failed: %s", exc)

    coins = load_coins()
    if not coins:
        logger.error("No coins loaded — exiting")
        return

    while True:
        bucket = _current_bucket()
        run_cycle(coins, bucket)
        # Sleep until the next bucket boundary (with a small buffer)
        now_ts    = int(datetime.now(timezone.utc).timestamp())
        next_ts   = (now_ts // config.RUN_INTERVAL + 1) * config.RUN_INTERVAL
        sleep_sec = max(60, next_ts - now_ts + 5)
        logger.info("Sleeping %ds until next bucket", sleep_sec)
        time.sleep(sleep_sec)


if __name__ == "__main__":
    main()
