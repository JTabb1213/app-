"""
News service — Google News RSS source
======================================
Hits the Google News RSS search endpoint (no API key required).
Returns the 4 most recent articles for the given coin name.

Query: "{coin_name} crypto"
URL:   https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en
"""

import logging
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

import requests

logger = logging.getLogger(__name__)

_TIMEOUT = 10
_MAX_ARTICLES = 4


def _coin_name(coin_id: str) -> str:
    """Convert 'bitcoin' → 'bitcoin', 'shiba-inu' → 'shiba inu'."""
    return coin_id.replace("-", " ")


def fetch(coin_id: str) -> list | None:
    """
    Returns a list of up to 4 article dicts:
      {title, url, source, published_at}
    or None on failure.
    """
    query = quote_plus(f"{_coin_name(coin_id)} crypto")
    url   = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

    try:
        resp = requests.get(url, timeout=_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("[news/google_rss] Fetch failed for %s: %s", coin_id, exc)
        return None

    try:
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")
        articles = []
        for item in items[:_MAX_ARTICLES]:
            title  = item.findtext("title", "").strip()
            link   = item.findtext("link",  "").strip()
            pub    = item.findtext("pubDate", "").strip()
            source_el = item.find("source")
            source = source_el.text.strip() if source_el is not None else "Google News"

            # Google News links are redirect URLs — use them as-is; they redirect to the article
            articles.append({
                "title":        title,
                "url":          link,
                "source":       source,
                "published_at": pub,
            })

        return articles if articles else None

    except ET.ParseError as exc:
        logger.warning("[news/google_rss] XML parse error for %s: %s", coin_id, exc)
        return None
