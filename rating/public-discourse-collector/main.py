#!/usr/bin/env python3
"""
Public Discourse Collector
==========================
Standalone service that runs on a daily schedule:

  1. Startup  — seed Redis from SQL (cold-start fallback).
  2. On tick  — for every coin in coins.json:
       a. Fetch Reddit sentiment
       b. Fetch News sentiment
       c. Fetch Google Trends search interest
       d. Compute 0-2 discourse score
       e. Write to SQL and Redis

Score breakdown (0-2):
  - Social Sentiment (Reddit + News) : 0-1
  - Search Interest (Google Trends)  : 0-1

Usage:
    NEWSAPI_KEY=your_key DATABASE_URL=... REDIS_URL=... python main.py
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

# ── Env loading ────────────────────────────────────────────────────────────────
def _load_env_files():
    root_env  = Path(__file__).resolve().parents[2] / ".env"
    local_env = Path(__file__).resolve().parent / ".env"
    for env_file in [root_env, local_env]:
        if not env_file.exists():
            continue
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip()
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value

_load_env_files()

import config
from fetchers import reddit as reddit_fetcher
from fetchers import news as news_fetcher
from fetchers import trends as trends_fetcher
from scorer import calculate_discourse_score

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)-30s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("public-discourse-collector")


# ── Coin list ──────────────────────────────────────────────────────────────────
def load_coins() -> list:
    path = Path(config.COINS_FILE)
    if not path.exists():
        logger.error(f"coins.json not found at {path}")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


# ── Per-coin processing ────────────────────────────────────────────────────────
def process_coin(coin: dict) -> dict:
    coin_id = coin["coin_id"]
    logger.info(f"Processing {coin_id} ({coin['symbol']})")

    # 1. Reddit sentiment
    reddit_result = reddit_fetcher.fetch_sentiment(coin)
    reddit_compound = reddit_result.get("avg_compound")
    logger.info(
        f"  Reddit: compound={reddit_compound}  posts={reddit_result.get('post_count', 0)}"
    )

    # 2. News sentiment
    news_result = news_fetcher.fetch_sentiment(coin)
    news_compound = news_result.get("avg_compound")
    logger.info(
        f"  News  : compound={news_compound}  articles={news_result.get('article_count', 0)}"
    )

    # 3. Google Trends interest
    trends_result = trends_fetcher.fetch_interest(coin)
    search_interest = trends_result.get("avg_interest")
    logger.info(
        f"  Trends: avg_interest={search_interest}  peak={trends_result.get('peak_interest')}"
    )

    # 4. Score (0-2)
    scores = calculate_discourse_score(
        reddit_compound=reddit_compound,
        news_compound=news_compound,
        search_interest=search_interest,
    )
    logger.info(
        f"  Score : {scores['score']}/2  "
        f"(sentiment={scores['social_sentiment']}, interest={scores['search_interest']})"
    )

    return {
        "coin_id": coin_id,
        "symbol":  coin["symbol"],
        "scores":  scores,
        "raw": {
            "reddit":  reddit_result,
            "news":    news_result,
            "trends":  trends_result,
        },
    }


# ── Main loop ──────────────────────────────────────────────────────────────────
def run_once():
    coins = load_coins()
    logger.info(f"Starting public discourse collection for {len(coins)} coins")

    results = []
    for coin in coins:
        try:
            result = process_coin(coin)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to process {coin['coin_id']}: {e}")

        time.sleep(2)  # avoid hammering APIs

    logger.info(f"Completed. Processed {len(results)}/{len(coins)} coins successfully.")
    return results


if __name__ == "__main__":
    while True:
        run_once()
        logger.info(f"Sleeping {config.SCHEDULE_INTERVAL_SECONDS}s until next run…")
        time.sleep(config.SCHEDULE_INTERVAL_SECONDS)
