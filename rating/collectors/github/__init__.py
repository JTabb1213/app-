"""
GitHub collector — router
==========================
Dispatches to the correct source based on coin["source"].

To add a new source (e.g. GitLab):
  1. Create sources/gitlab.py  implementing  fetch(coin, token, base_url) -> dict | None
  2. Import and register it below.
"""

import logging

from .sources import github_api
# from .sources import gitlab   # future

logger = logging.getLogger(__name__)

SOURCE_MAP = {
    "github_api": github_api,
}


def fetch(coin: dict, token: str = "",
          base_url: str = "https://api.github.com") -> dict | None:
    source = coin.get("source", "github_api")
    mod    = SOURCE_MAP.get(source)
    if mod is None:
        logger.warning(f"[github] Unknown source '{source}' for {coin.get('coin_id')}")
        return None
    return mod.fetch(coin, token=token, base_url=base_url)


__all__ = ["fetch"]
