"""
Configuration for collectors-primary service.

Collector for: Kraken, Coinbase, Binance (US-compliant exchanges).
Only needs Redis Stream + exchange websocket settings.
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
STREAM_TRADES_KEY = os.getenv("STREAM_TRADES_KEY", "stream:trades")
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
# Kraken
# ---------------------------------------------------------------------------
KRAKEN_WS_URL = os.getenv("KRAKEN_WS_URL", "wss://ws.kraken.com/v2")
KRAKEN_REST_URL = os.getenv(
    "KRAKEN_REST_URL", "https://api.kraken.com/0/public/AssetPairs",
)
KRAKEN_CHUNK_SIZE = int(os.getenv("KRAKEN_CHUNK_SIZE", "200"))

# ---------------------------------------------------------------------------
# Coinbase
# ---------------------------------------------------------------------------
COINBASE_WS_URL = os.getenv("COINBASE_WS_URL", "wss://ws-feed.exchange.coinbase.com")
COINBASE_REST_URL = os.getenv(
    "COINBASE_REST_URL", "https://api.exchange.coinbase.com/products",
)

# ---------------------------------------------------------------------------
# Binance.US (US-compliant endpoint)
# ---------------------------------------------------------------------------
BINANCE_WS_URL = os.getenv("BINANCE_WS_URL", "wss://stream.binance.us:9443")
BINANCE_REST_URL = os.getenv(
    "BINANCE_REST_URL", "https://api.binance.us/api/v3/exchangeInfo",
)

# ---------------------------------------------------------------------------
# Quote currencies
# ---------------------------------------------------------------------------
QUOTE_CURRENCIES = [
    q.strip().upper()
    for q in os.getenv("QUOTE_CURRENCIES", "USD").split(",")
]

# ---------------------------------------------------------------------------
# Logging & Health
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
HEALTH_PORT = int(os.getenv("PORT", os.getenv("HEALTH_PORT", "8081")))
