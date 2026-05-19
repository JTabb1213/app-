"""
Public Discourse collector
==========================
Public API used by the score orchestrator:

    fetch(coin, newsapi_key, serpapi_key)  -> dict | None
    prefetch_trends_batch(coins, serpapi_key) -> dict

Sources live in sources/:
    reddit.py         — Reddit VADER sentiment
    newsapi.py        — NewsAPI VADER sentiment
    serpapi_trends.py — Google Trends search interest (batched)

The aggregator.py module combines all three into one result dict.
To add a new source, implement fetch() in sources/ and add it to aggregator.py.
"""

import logging

from .aggregator import fetch
from .sources.serpapi_trends import prefetch_batch as prefetch_trends_batch

logger = logging.getLogger(__name__)

__all__ = ["fetch", "prefetch_trends_batch"]
