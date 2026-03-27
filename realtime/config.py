"""
Configuration for the realtime market data ingestion server.

All settings are loaded from environment variables with sensible defaults.
See .env.example for documentation on each setting.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL")

# ---------------------------------------------------------------------------
# Alias file
# ---------------------------------------------------------------------------
# Path to the shared coin_aliases.json used across the whole project.
# Default assumes this server lives at <project-root>/realtime/
ALIAS_JSON_PATH = os.getenv(
    "ALIAS_JSON_PATH",
    os.path.join(os.path.dirname(__file__), "..", "data", "coin_aliases.json"),
)

# ---------------------------------------------------------------------------
# TTL for realtime data in Redis (seconds)
# ---------------------------------------------------------------------------
# Acts as a safety valve: if this service crashes, stale prices auto-expire
# rather than persisting in Redis forever.  The service refreshes each key's
# TTL on every write, so active coins are never affected.
#
# 43200 s (12 h) accommodates illiquid coins that trade only once or twice
# a day — their last known price remains readable until the next tick arrives.
# The `timestamp` field inside the stored JSON tells consumers exactly how
# old the data is, so staleness is always transparent regardless of TTL.
# Never set this to 0 (no expiry): a crashed service would leave
# permanently stale prices in Redis with no indication of staleness.
RT_PRICE_TTL = int(os.getenv("RT_PRICE_TTL", "300")) # 43200 = 12 hours if needed

# ---------------------------------------------------------------------------
# Batch settings for Redis writes
# ---------------------------------------------------------------------------
# Flush to Redis when this many ticks have accumulated...
BATCH_MAX_SIZE = int(os.getenv("BATCH_MAX_SIZE", "100"))
# ...or when this many milliseconds have elapsed since the last flush,
# whichever comes first.
BATCH_INTERVAL_MS = int(os.getenv("BATCH_INTERVAL_MS", "500"))

# ---------------------------------------------------------------------------
# Kraken exchange settings
# ---------------------------------------------------------------------------
KRAKEN_WS_URL = os.getenv("KRAKEN_WS_URL", "wss://ws.kraken.com/v2")
KRAKEN_REST_URL = os.getenv(
    "KRAKEN_REST_URL", "https://api.kraken.com/0/public/AssetPairs",
)
# Max pairs per websocket connection (Kraken limit is ~250, stay under)
KRAKEN_CHUNK_SIZE = int(os.getenv("KRAKEN_CHUNK_SIZE", "200"))

# ---------------------------------------------------------------------------
# Quote currencies to track
# ---------------------------------------------------------------------------
# Only subscribe to pairs quoted in these currencies.
# Comma-separated in env, e.g. "USD,EUR"
QUOTE_CURRENCIES = [
    q.strip().upper()
    for q in os.getenv("QUOTE_CURRENCIES", "USD").split(",")
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ---------------------------------------------------------------------------
# Health check server (Cloud Run injects PORT automatically)
# ---------------------------------------------------------------------------
HEALTH_PORT = int(os.getenv("PORT", "8080"))
