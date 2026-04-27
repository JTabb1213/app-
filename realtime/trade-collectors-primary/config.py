"""
Configuration for trade-collectors-primary service.

Collects individual trade executions from: Kraken, Coinbase, Binance.
Pushes raw trade data to a dedicated Redis Stream for volume aggregation.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL")

# ---------------------------------------------------------------------------
# Redis Stream (producer settings)
# ---------------------------------------------------------------------------
STREAM_KEY = os.getenv("VOLUME_STREAM_KEY", "stream:trades:volume")
STREAM_MAX_LEN = int(os.getenv("STREAM_MAX_LEN", "50000"))
STREAM_PRODUCER_BATCH_SIZE = int(os.getenv("STREAM_PRODUCER_BATCH_SIZE", "50"))
STREAM_PRODUCER_FLUSH_MS = int(os.getenv("STREAM_PRODUCER_FLUSH_MS", "500"))

# ---------------------------------------------------------------------------
# Alias file (used for symbol discovery)
# ---------------------------------------------------------------------------
ALIAS_JSON_PATH = os.getenv(
    "ALIAS_JSON_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "coin_aliases.json"),
)

# ---------------------------------------------------------------------------
# Exchange endpoints
# ---------------------------------------------------------------------------
KRAKEN_WS_URL = os.getenv("KRAKEN_WS_URL", "wss://ws.kraken.com/v2")
COINBASE_WS_URL = os.getenv("COINBASE_WS_URL", "wss://ws-feed.exchange.coinbase.com")
BINANCE_WS_URL = os.getenv("BINANCE_WS_URL", "wss://stream.binance.us:9443")

# ---------------------------------------------------------------------------
# Logging & Health
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
HEALTH_PORT = int(os.getenv("PORT", os.getenv("HEALTH_PORT", "8084")))
