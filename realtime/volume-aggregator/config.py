"""
Volume Aggregator configuration.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Stream
VOLUME_STREAM_KEY = os.getenv("VOLUME_STREAM_KEY", "stream:trades:volume")
VOLUME_CONSUMER_GROUP = os.getenv("VOLUME_CONSUMER_GROUP", "volume-aggregator")
VOLUME_CONSUMER_NAME = os.getenv("VOLUME_CONSUMER_NAME", "agg-1")

# Aggregation
VOLUME_FLUSH_INTERVAL_MS = int(os.getenv("VOLUME_FLUSH_INTERVAL_MS", "5000"))
VOLUME_BUCKET_SECONDS = int(os.getenv("VOLUME_BUCKET_SECONDS", "60"))
VOLUME_WINDOWS = os.getenv("VOLUME_WINDOWS", "5m,30m,4h,24h")
VOLUME_KEY_TTL_HOURS = int(os.getenv("VOLUME_KEY_TTL_HOURS", "25"))
VOLUME_PRUNE_INTERVAL_SECONDS = int(os.getenv("VOLUME_PRUNE_INTERVAL_SECONDS", "300"))

# Alias file
ALIAS_JSON_PATH = os.getenv(
    "ALIAS_JSON_PATH",
    os.path.join(os.path.dirname(__file__), "data", "coin_aliases.json"),
)

# Logging / Health
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
HEALTH_PORT = int(os.getenv("HEALTH_PORT", "8086"))
