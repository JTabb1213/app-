"""
Configuration for the WebSocket broadcast server.

All settings are loaded from environment variables with sensible defaults.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL")

# ---------------------------------------------------------------------------
# WebSocket server
# ---------------------------------------------------------------------------
WS_HOST = os.getenv("WS_HOST", "0.0.0.0")
# Cloud Run injects PORT; fall back to WS_PORT, then 8765 for local/VM use
WS_PORT = int(os.getenv("PORT") or os.getenv("WS_PORT", "8765"))

# Maximum subscriptions a single client can have at once.
# Prevents abuse — a client subscribing to 10,000 coins would
# effectively become a "subscribe to everything" connection.
MAX_SUBSCRIPTIONS_PER_CLIENT = int(
    os.getenv("MAX_SUBSCRIPTIONS_PER_CLIENT", "50")
)

# ---------------------------------------------------------------------------
# Health check (for container orchestration / load balancer probes)
# ---------------------------------------------------------------------------
HEALTH_PORT = int(os.getenv("HEALTH_PORT", "8080"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
