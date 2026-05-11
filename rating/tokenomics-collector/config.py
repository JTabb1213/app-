"""
Tokenomics Collector — Configuration
=====================================
Loads from the project root .env first (so all shared secrets are picked up),
then the local .env for any overrides specific to this service.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Root .env first (shared secrets), then local .env for overrides
_root_env  = Path(__file__).resolve().parents[2] / ".env"
_local_env = Path(__file__).resolve().parent / ".env"
load_dotenv(_root_env,  override=False)
load_dotenv(_local_env, override=True)

# ── CoinGecko ─────────────────────────────────────────────────────────────────
COINGECKO_BASE_URL: str = "https://api.coingecko.com/api/v3"

# Max coins per /coins/markets request (CoinGecko hard cap = 250)
BATCH_SIZE: int = int(os.getenv("COINGECKO_BATCH_SIZE", "100"))

# ── Storage ───────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
REDIS_URL: str    = os.getenv("REDIS_URL", "")

# TTL for Redis keys (default: 8 days — generous buffer over the weekly schedule)
REDIS_TTL: int = int(os.getenv("REDIS_TTL", str(8 * 24 * 3600)))

# Redis key pattern: crypto:tokenomics:{coin_id}
REDIS_KEY_PREFIX: str = "crypto:tokenomics"

# ── Scheduler ─────────────────────────────────────────────────────────────────
# How often to refresh all coins (seconds).  Default: 7 days.
SCHEDULE_INTERVAL_SECONDS: int = int(
    os.getenv("SCHEDULE_INTERVAL_SECONDS", str(7 * 24 * 3600))
)

# ── Coins to track ────────────────────────────────────────────────────────────
COINS_FILE: str = os.getenv(
    "COINS_FILE",
    str(Path(__file__).parent / "coins.json"),
)
