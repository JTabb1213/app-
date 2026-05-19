"""
News collector — config
"""
import os

DATABASE_URL  = os.getenv("DATABASE_URL", "postgresql://dev:devpassword@postgres:5432/cryptorating")
REDIS_URL     = os.getenv("REDIS_URL",    "redis://redis:6379")

# How long news stays fresh in Redis (seconds) — 1 hour
REDIS_TTL     = int(os.getenv("NEWS_REDIS_TTL", str(3600)))

# How often the collector runs a full refresh cycle (seconds) — 2 hours
RUN_INTERVAL  = int(os.getenv("NEWS_RUN_INTERVAL", str(2 * 3600)))

# Pause between per-coin RSS fetches to avoid being blocked (seconds)
REQUEST_DELAY = float(os.getenv("NEWS_REQUEST_DELAY", "2.0"))

# Max articles stored per coin
MAX_ARTICLES  = int(os.getenv("NEWS_MAX_ARTICLES", "4"))

LOG_LEVEL     = os.getenv("LOG_LEVEL", "INFO")
