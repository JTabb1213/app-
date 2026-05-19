"""
Score Orchestrator — Configuration
=====================================
All environment variables for the orchestrator service.
Loads from the project root .env first, then local .env for overrides.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

_root_env  = Path(__file__).resolve().parents[2] / ".env"
_local_env = Path(__file__).resolve().parent / ".env"
load_dotenv(_root_env,  override=False)
load_dotenv(_local_env, override=True)

# ── Storage ────────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
REDIS_URL: str    = os.getenv("REDIS_URL", "")

# TTL for rating Redis keys — generous buffer over the weekly schedule (8 days)
REDIS_TTL: int = int(os.getenv("REDIS_TTL", str(8 * 24 * 3600)))

# ── External APIs ──────────────────────────────────────────────────────────────
COVALENT_API_KEY: str   = os.getenv("COVALENT_API_KEY", "")
COINGECKO_API_KEY: str  = os.getenv("COINGECKO_API_KEY", "")
GITHUB_TOKEN: str       = os.getenv("GITHUB_TOKEN", "")
NEWSAPI_KEY: str       = os.getenv("NEWSAPI_KEY", "")
SERPAPI_KEY: str       = os.getenv("SERPAPI_KEY", "")

# ── Discourse rate-limit cache ─────────────────────────────────────────────────
# Per-coin JSON files are written here after every successful API call.
# If a call fails (or the cache is still fresh), the cached result is reused
# so the orchestrator never writes a zero-score due to a transient rate limit.
DISCOURSE_CACHE_DIR: str        = os.getenv("DISCOURSE_CACHE_DIR", "/tmp/ccs_discourse")
DISCOURSE_REDDIT_TTL_HOURS: int = int(os.getenv("DISCOURSE_REDDIT_TTL_HOURS",  "2"))
DISCOURSE_NEWS_TTL_HOURS: int   = int(os.getenv("DISCOURSE_NEWS_TTL_HOURS",    "6"))
DISCOURSE_TRENDS_TTL_HOURS: int = int(os.getenv("DISCOURSE_TRENDS_TTL_HOURS", "168"))

# ── Scheduler ─────────────────────────────────────────────────────────────────
# How often to run the full scoring cycle. Default: 7 days.
SCHEDULE_INTERVAL_SECONDS: int = int(
    os.getenv("SCHEDULE_INTERVAL_SECONDS", str(7 * 24 * 3600))
)

# Coin lists are sourced exclusively from CoinRegistry (data/coin_aliases.json).
# The old per-collector coins.json files have been removed.
