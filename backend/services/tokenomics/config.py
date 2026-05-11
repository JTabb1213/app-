"""
Tokenomics — Backend Configuration
====================================
Read-only.  This module knows nothing about CoinGecko or any external API.
Data is populated exclusively by rating/tokenomics-collector.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

_BACKEND_ENV = Path(__file__).parents[2] / ".env"
load_dotenv(_BACKEND_ENV, override=False)

# -- Redis ---------------------------------------------------------------------
REDIS_URL: str = os.getenv("REDIS_URL", "")

# -- Postgres ------------------------------------------------------------------
DATABASE_URL: str = os.getenv("DATABASE_URL", "")

# -- Cache key prefix ----------------------------------------------------------
# Must match REDIS_KEY_PREFIX in rating/tokenomics-collector/config.py
CACHE_KEY_PREFIX: str = "crypto:tokenomics"
