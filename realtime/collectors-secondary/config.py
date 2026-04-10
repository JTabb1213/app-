"""
Configuration for collectors-secondary service.

Collector for: Gate.io, MEXC, OKX, Pionex (global exchanges).
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
# Gate.io
# ---------------------------------------------------------------------------
GATEIO_WS_URL = os.getenv("GATEIO_WS_URL", "wss://api.gateio.ws/ws/v4/")
GATEIO_REST_URL = os.getenv(
    "GATEIO_REST_URL", "https://api.gateio.ws/api/v4/spot/currency_pairs",
)
GATEIO_PING_INTERVAL = int(os.getenv("GATEIO_PING_INTERVAL", "10"))

# ---------------------------------------------------------------------------
# MEXC  (blocks US IPs — deploy outside US)
# ---------------------------------------------------------------------------
MEXC_WS_URL = os.getenv("MEXC_WS_URL", "wss://wbs.mexc.com/ws")
MEXC_REST_URL = os.getenv(
    "MEXC_REST_URL", "https://api.mexc.com/api/v3/exchangeInfo",
)

# ---------------------------------------------------------------------------
# OKX
# ---------------------------------------------------------------------------
OKX_WS_URL = os.getenv("OKX_WS_URL", "wss://ws.okx.com:8443/ws/v5/public")
OKX_REST_URL = os.getenv(
    "OKX_REST_URL", "https://www.okx.com/api/v5/public/instruments?instType=SPOT",
)

# ---------------------------------------------------------------------------
# Pionex  (use .us domain for US users)
# ---------------------------------------------------------------------------
PIONEX_WS_URL = os.getenv("PIONEX_WS_URL", "wss://ws.pionex.us/wsPub")
PIONEX_REST_URL = os.getenv(
    "PIONEX_REST_URL", "https://api.pionex.com/api/v1/common/symbols",
)

# ---------------------------------------------------------------------------
# Quote currencies
# ---------------------------------------------------------------------------
QUOTE_CURRENCIES = [
    q.strip().upper()
    for q in os.getenv("QUOTE_CURRENCIES", "USDT").split(",")
]

# ---------------------------------------------------------------------------
# Logging & Health
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
HEALTH_PORT = int(os.getenv("PORT", os.getenv("HEALTH_PORT", "8082")))
