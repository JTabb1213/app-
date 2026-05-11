"""
Holder Diversity Collector — Configuration
==========================================
Loads from rating/holder-diversity-collector/.env first,
then falls back to nothing (all values must be explicit for a standalone service).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

_ENV = Path(__file__).parent / ".env"
load_dotenv(_ENV, override=True)

# ── Covalent ───────────────────────────────────────────────────────────────────
COVALENT_API_KEY: str = os.getenv("COVALENT_API_KEY", "")
COVALENT_BASE_URL: str = "https://api.covalenthq.com/v1"

# Chain name → Covalent numeric chain id
COVALENT_CHAIN_IDS: dict = {
    "ethereum": 1,
    "polygon": 137,
    "bsc": 56,
    "avalanche": 43114,
    "arbitrum": 42161,
    "optimism": 10,
    "base": 8453,
}

# How many holders to page through per token (Covalent page size max = 1000)
FETCH_LIMIT: int = int(os.getenv("FETCH_LIMIT", "1000"))

# ── Storage ────────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
REDIS_URL: str = os.getenv("REDIS_URL", "")

# TTL for Redis keys (default: 8 days — generous buffer over the weekly schedule)
REDIS_TTL: int = int(os.getenv("REDIS_TTL", str(8 * 24 * 3600)))

# Redis key pattern: crypto:holder_diversity:{chain}:{coin_id}
REDIS_KEY_PREFIX: str = "crypto:holder_diversity"

# ── Scheduler ──────────────────────────────────────────────────────────────────
# How often to refresh all coins (seconds).  Default: 7 days.
SCHEDULE_INTERVAL_SECONDS: int = int(os.getenv("SCHEDULE_INTERVAL_SECONDS", str(7 * 24 * 3600)))

# ── Coins to track ─────────────────────────────────────────────────────────────
# Path to a JSON file mapping coin_id → {chain, contract_address}.
# If not set, the service will look for coins.json in its own directory.
COINS_FILE: str = os.getenv(
    "COINS_FILE",
    str(Path(__file__).parent / "coins.json"),
)
