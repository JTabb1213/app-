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
COVALENT_API_KEY: str  = os.getenv("COVALENT_API_KEY", "")
GITHUB_TOKEN: str      = os.getenv("GITHUB_TOKEN", "")
NEWSAPI_KEY: str       = os.getenv("NEWSAPI_KEY", "")

# ── Scheduler ─────────────────────────────────────────────────────────────────
# How often to run the full scoring cycle. Default: 7 days.
SCHEDULE_INTERVAL_SECONDS: int = int(
    os.getenv("SCHEDULE_INTERVAL_SECONDS", str(7 * 24 * 3600))
)

# ── Coins files ────────────────────────────────────────────────────────────────
# Each collector has its own coin list with the fields it needs.
_rating_dir = Path(__file__).resolve().parents[1]

GITHUB_COINS_FILE: str = os.getenv(
    "GITHUB_COINS_FILE",
    str(_rating_dir / "github-collector" / "coins.json"),
)
HOLDER_DIVERSITY_COINS_FILE: str = os.getenv(
    "HOLDER_DIVERSITY_COINS_FILE",
    str(_rating_dir / "holder-diversity-collector" / "coins.json"),
)
TOKENOMICS_COINS_FILE: str = os.getenv(
    "TOKENOMICS_COINS_FILE",
    str(_rating_dir / "tokenomics-collector" / "coins.json"),
)
PUBLIC_DISCOURSE_COINS_FILE: str = os.getenv(
    "PUBLIC_DISCOURSE_COINS_FILE",
    str(_rating_dir / "public-discourse-collector" / "coins.json"),
)
