"""
Shared disk-cache helpers for all public discourse sources.

Each coin's cached data lives in a single JSON file at:
  {DISCOURSE_CACHE_DIR}/{coin_id}.json

The file is a flat dict keyed by  "{source}_value"  and  "{source}_at"
(unix timestamp).  Each source reads/writes only its own keys, so all
three sources share one file per coin without conflicts.

TTLs (overridable via env):
  DISCOURSE_REDDIT_TTL_HOURS   default 2
  DISCOURSE_NEWS_TTL_HOURS     default 6
  DISCOURSE_TRENDS_TTL_HOURS   default 168  (7 days — matches weekly cadence)
"""

import json
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(os.getenv("DISCOURSE_CACHE_DIR", "/tmp/ccs_discourse"))
TTL = {
    "reddit": int(os.getenv("DISCOURSE_REDDIT_TTL_HOURS",  "2"))   * 3600,
    "news":   int(os.getenv("DISCOURSE_NEWS_TTL_HOURS",    "6"))   * 3600,
    "trends": int(os.getenv("DISCOURSE_TRENDS_TTL_HOURS", "168"))  * 3600,
}

# Sentinel — distinguishes "not in cache" from a cached None value.
MISS = object()


def cache_path(coin_id: str) -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR / f"{coin_id}.json"


def load(coin_id: str) -> dict:
    try:
        p = cache_path(coin_id)
        if p.exists():
            return json.loads(p.read_text())
    except Exception:
        pass
    return {}


def save(coin_id: str, cache: dict) -> None:
    try:
        cache_path(coin_id).write_text(json.dumps(cache))
    except Exception as exc:
        logger.warning(f"[DiscourseCache] Could not write cache for {coin_id}: {exc}")


def is_fresh(cache: dict, source: str) -> bool:
    return (time.time() - cache.get(f"{source}_at", 0)) < TTL[source]


def get(cache: dict, source: str):
    """Return cached value if fresh, else MISS."""
    if is_fresh(cache, source) and f"{source}_value" in cache:
        return cache[f"{source}_value"]
    return MISS


def put(cache: dict, source: str, value) -> None:
    """Write a value + timestamp into the in-memory cache dict."""
    cache[f"{source}_value"] = value
    cache[f"{source}_at"]    = time.time()
