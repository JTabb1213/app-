"""
Holder Diversity - Backend Configuration
Reads Redis URL and DB URL from the backend .env.
This module knows nothing about Covalent, Etherscan, or any external API.
Data is populated by the standalone rating/holder-diversity-collector service.
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

# -- Cache key -----------------------------------------------------------------
# Must match the key written by rating/holder-diversity-collector
CACHE_KEY_PREFIX: str = "crypto:holder_diversity"
