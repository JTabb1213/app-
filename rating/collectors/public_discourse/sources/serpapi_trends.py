"""
SerpAPI Google Trends source — fetches relative search interest (0-100) for
a coin's primary keyword via Google Trends (12-month weekly data).

Batching
--------
The orchestrator calls prefetch_batch() ONCE before the per-coin loop.
It groups all keywords into batches of BATCH_SIZE (5), makes one API call
per batch, and writes the result straight to the disk cache.
Per-coin fetch() then reads purely from cache — zero extra API calls.

Quota: ceil(N / 5) calls per run.  50 coins = 10 calls (80% savings vs 1/coin).

Score formula: 60% most-recent week + 40% 4-week average.
  Rationale: rewards a recent spike while smoothing single-week noise,
  appropriate for a weekly scoring cadence.

Cache key: "trends"   TTL: DISCOURSE_TRENDS_TTL_HOURS (default 168 h / 7 days)
"""

import logging
import os
import time

import requests

from . import cache as disk_cache

logger = logging.getLogger(__name__)

_BASE        = os.getenv("SERPAPI_BASE_URL", "https://serpapi.com/search")
_HEADERS     = {"User-Agent": "ccs-discourse-collector/1.0"}
BATCH_SIZE   = 5   # Google Trends allows up to 5 keywords per request
BATCH_DELAY  = 2   # seconds between consecutive batch calls


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _api_call(keywords: list, serpapi_key: str) -> dict | None:
    """Single SerpAPI request for up to BATCH_SIZE keywords."""
    params = {
        "engine":  "google_trends",
        "q":       ",".join(keywords),
        "api_key": serpapi_key,
    }
    try:
        resp = requests.get(_BASE, params=params, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            logger.error(f"[SerpAPI] error: {data['error']}")
            return None
        return data
    except Exception as exc:
        logger.error(f"[SerpAPI] request failed: {exc}")
        return None


def _parse_interest(data: dict, keyword: str) -> float | None:
    """
    Extract a 0-100 score for one keyword from a SerpAPI response.
    Formula: 60% most-recent week + 40% 4-week average.
    """
    timeline = data.get("interest_over_time", {}).get("timeline_data", [])
    if not timeline:
        return None
    kw_lower = keyword.lower()
    values   = []
    for period in timeline:
        match = next(
            (v for v in period.get("values", []) if v.get("query", "").lower() == kw_lower),
            None,
        )
        if match is not None:
            values.append(match.get("extracted_value", 0))
    if not values:
        return None
    latest   = values[-1]
    recent_4 = values[-4:] if len(values) >= 4 else values
    avg_4    = sum(recent_4) / len(recent_4)
    return round(0.6 * latest + 0.4 * avg_4, 2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def prefetch_batch(coins: list, serpapi_key: str) -> dict:
    """
    Pre-fetch Google Trends for ALL discourse coins in batched API calls.

    Call this ONCE from the orchestrator before the per-coin scoring loop.
    Results are persisted to the disk cache so that per-coin fetch() calls
    cost zero additional API requests.

    Args:
        coins:       list of coin dicts (must have "coin_id" and optionally
                     "search_queries")
        serpapi_key: SerpAPI API key

    Returns:
        dict mapping coin_id -> search_interest score (0-100)
    """
    if not serpapi_key:
        logger.warning("[SerpAPI] No SERPAPI_KEY — skipping batch prefetch")
        return {}

    # Map primary keyword -> coin_id
    kw_to_coin: dict[str, str] = {}
    for c in coins:
        queries = c.get("search_queries", [c["coin_id"]])
        kw_to_coin[queries[0].lower()] = c["coin_id"]

    keywords  = list(kw_to_coin.keys())
    results:  dict[str, float] = {}
    api_calls = 0
    n_batches = -(-len(keywords) // BATCH_SIZE)   # ceiling division

    logger.info(
        f"[SerpAPI] Prefetching {len(keywords)} keywords in "
        f"{n_batches} batch(es) (batch_size={BATCH_SIZE})"
    )

    for i in range(0, len(keywords), BATCH_SIZE):
        batch      = keywords[i : i + BATCH_SIZE]
        api_calls += 1
        logger.info(f"[SerpAPI] Batch {api_calls}/{n_batches}: {batch}")

        data = _api_call(batch, serpapi_key)
        if data is None:
            logger.warning(f"[SerpAPI] Batch {api_calls} failed — skipping {batch}")
        else:
            for kw in batch:
                coin_id = kw_to_coin[kw]
                value   = _parse_interest(data, kw)
                if value is None:
                    logger.warning(f"[SerpAPI] No data for '{kw}' ({coin_id})")
                    continue
                coin_cache = disk_cache.load(coin_id)
                disk_cache.put(coin_cache, "trends", value)
                disk_cache.save(coin_id, coin_cache)
                results[coin_id] = value

        if i + BATCH_SIZE < len(keywords):
            time.sleep(BATCH_DELAY)

    logger.info(
        f"[SerpAPI] Prefetch complete — {len(results)}/{len(keywords)} cached "
        f"in {api_calls} API call(s)"
    )
    return results


def fetch(coin: dict, cache: dict, serpapi_key: str = "") -> float | None:
    """
    Return search interest from the disk cache (written by prefetch_batch).
    Falls back to a single-coin API call if the cache is missing or expired.
    """
    hit = disk_cache.get(cache, "trends")
    if hit is not disk_cache.MISS:
        return hit

    key = serpapi_key or os.getenv("SERPAPI_KEY", "")
    if not key:
        return cache.get("trends_value")

    queries = coin.get("search_queries", [coin.get("symbol", coin["coin_id"])])
    kw      = queries[0].lower()
    logger.info(f"[Trends] {coin['coin_id']}: cache miss — single-coin fallback")
    data = _api_call([kw], key)
    if data is None:
        return cache.get("trends_value")
    value = _parse_interest(data, kw)
    if value is not None:
        disk_cache.put(cache, "trends", value)
    return value
