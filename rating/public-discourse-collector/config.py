"""
Public Discourse Collector — Configuration
==========================================
Loads from rating/public-discourse-collector/.env first,
then falls back to the root .env.

Sources:
  - Reddit public JSON API (no key required)
  - NewsAPI (free key required — https://newsapi.org)
  - Google Trends via pytrends (no key required)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

_ENV = Path(__file__).parent / ".env"
load_dotenv(_ENV, override=True)

# ── NewsAPI ────────────────────────────────────────────────────────────────────
NEWSAPI_KEY: str      = os.getenv("NEWSAPI_KEY", "")
NEWSAPI_BASE_URL: str = os.getenv("NEWSAPI_BASE_URL", "https://newsapi.org/v2")

# ── Reddit ─────────────────────────────────────────────────────────────────────
REDDIT_API_BASE_URL: str = os.getenv("REDDIT_API_BASE_URL", "https://www.reddit.com")
REDDIT_POSTS_PER_SUB: int = int(os.getenv("REDDIT_POSTS_PER_SUB", "25"))
REDDIT_TIME_FILTER: str   = os.getenv("REDDIT_TIME_FILTER", "week")  # day|week|month

# ── Google Trends ──────────────────────────────────────────────────────────────
TRENDS_TIMEFRAME: str = os.getenv("TRENDS_TIMEFRAME", "today 1-m")  # last 30 days

# ── Storage ────────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
REDIS_URL: str    = os.getenv("REDIS_URL", "")

# TTL for Redis keys — 24 hours (discourse data changes daily)
REDIS_TTL: int = int(os.getenv("REDIS_TTL", str(24 * 3600)))

# Redis key pattern: crypto:public_discourse:{coin_id}
REDIS_KEY_PREFIX: str = "crypto:public_discourse"

# ── Scheduler ─────────────────────────────────────────────────────────────────
# How often to refresh all coins (seconds). Default: 24 hours.
SCHEDULE_INTERVAL_SECONDS: int = int(os.getenv("SCHEDULE_INTERVAL_SECONDS", str(24 * 3600)))

# ── Coins source ──────────────────────────────────────────────────────────────
# Path to coins.json in this directory
COINS_FILE: str = os.getenv(
    "COINS_FILE",
    str(Path(__file__).parent / "coins.json"),
)
