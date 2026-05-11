"""
Configuration for the candle-aggregator service.
All values can be overridden via environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL      = os.getenv("DATABASE_URL")
DATABASE_URL_IPV4 = os.getenv("DATABASE_URL_IPV4")

# ── Schedule ──────────────────────────────────────────────────────────────────
# How often to run all roll-ups (in minutes).
# 60 = once per hour. Lower for faster testing (e.g. 5).
RUN_INTERVAL_MINUTES = int(os.getenv("RUN_INTERVAL_MINUTES", "60"))

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
