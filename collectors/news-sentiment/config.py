"""
News Sentiment Collector — config
"""
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dev:devpassword@postgres:5432/cryptorating")

GOOGLE_NEWS_RSS_BASE_URL = os.getenv("GOOGLE_NEWS_RSS_BASE_URL", "https://news.google.com/rss/search")

# How often the service runs a full collection cycle (seconds). Default 4 hours.
RUN_INTERVAL = int(os.getenv("NEWS_SENTIMENT_RUN_INTERVAL", str(4 * 3600)))

# Pause between per-coin RSS fetches to avoid being rate-limited (seconds).
REQUEST_DELAY = float(os.getenv("NEWS_SENTIMENT_REQUEST_DELAY", "2.0"))

# Max articles to collect per coin per run.
MAX_ARTICLES = int(os.getenv("NEWS_SENTIMENT_MAX_ARTICLES", "10"))

# Path to coin_aliases.json (mounted from repo root /data).
COIN_ALIASES_PATH = os.getenv("COIN_ALIASES_PATH", "/data/coin_aliases.json")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
