"""
Configuration for trade-collectors-secondary service.

Collects individual trade executions from: OKX, Gate.io, MEXC, Pionex.
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
OKX_WS_URL = os.getenv("OKX_WS_URL", "wss://ws.okx.com:8443/ws/v5/public")
GATEIO_WS_URL = os.getenv("GATEIO_WS_URL", "wss://api.gateio.ws/ws/v4/")
MEXC_WS_URL = os.getenv("MEXC_WS_URL", "wss://wbs.mexc.com/ws")
BYBIT_WS_URL = os.getenv("BYBIT_WS_URL", "wss://stream.bybit.com/v5/public/spot")
PIONEX_WS_URL = os.getenv("PIONEX_WS_URL", "wss://ws.pionex.us/wsPub")

# ---------------------------------------------------------------------------
# Logging & Health
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
HEALTH_PORT = int(os.getenv("PORT", os.getenv("HEALTH_PORT", "8085")))
