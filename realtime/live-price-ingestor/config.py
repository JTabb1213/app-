"""
Configuration for the ingestor service.

Reads raw ticks from Redis Stream, normalizes them, computes
aggregates, and publishes to Redis cache + pub/sub.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL")

# ---------------------------------------------------------------------------
# Redis Stream (consumer settings)
# ---------------------------------------------------------------------------
STREAM_TRADES_KEY = os.getenv("STREAM_TRADES_KEY", "stream:trades")
STREAM_CONSUMER_GROUP = os.getenv("STREAM_CONSUMER_GROUP", "normalizer")
STREAM_CONSUMER_NAME = os.getenv("STREAM_CONSUMER_NAME", "consumer-1")
STREAM_CONSUMER_BATCH_SIZE = int(os.getenv("STREAM_CONSUMER_BATCH_SIZE", "100"))
STREAM_CONSUMER_BLOCK_MS = int(os.getenv("STREAM_CONSUMER_BLOCK_MS", "2000"))

# ---------------------------------------------------------------------------
# Alias file (used by normalizer for symbol resolution)
# ---------------------------------------------------------------------------
ALIAS_JSON_PATH = os.getenv(
    "ALIAS_JSON_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "coin_aliases.json"),
)

# ---------------------------------------------------------------------------
# Redis writer / batching
# ---------------------------------------------------------------------------
BATCH_MAX_SIZE = int(os.getenv("BATCH_MAX_SIZE", "100"))
BATCH_INTERVAL_MS = int(os.getenv("BATCH_INTERVAL_MS", "2000"))
RT_PRICE_TTL = int(os.getenv("RT_PRICE_TTL", "300"))

# ---------------------------------------------------------------------------
# Logging & Health
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
HEALTH_PORT = int(os.getenv("PORT", os.getenv("HEALTH_PORT", "8083")))
