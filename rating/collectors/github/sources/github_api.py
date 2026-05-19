"""
GitHub Activity source — github.com REST API
=============================================
Fetches repo stats for any project hosted on github.com or a GitHub Enterprise
instance. Used for Community & Dev Activity scoring.

Returned dict matches the shape defined in base.py.
"""

import logging
import re
import time
from datetime import datetime, timezone
from typing import Optional

import requests

logger   = logging.getLogger(__name__)
_SESSION: requests.Session | None = None


def _get_session(token: str) -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update({
            "Accept": "application/vnd.github+json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        })
    return _SESSION


def _get(url: str, token: str, params: dict | None = None):
    s = _get_session(token)
    try:
        resp = s.get(url, params=params, timeout=15)
        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait  = max(reset - int(time.time()), 1)
            logger.warning(f"GitHub rate limited — sleeping {wait}s")
            time.sleep(wait)
            resp = s.get(url, params=params, timeout=15)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        logger.error(f"GitHub request error {url}: {exc}")
        return None


def _total_commits(owner: str, repo: str, base_url: str, token: str) -> int:
    data = _get(f"{base_url}/repos/{owner}/{repo}/contributors",
                token, params={"per_page": 100})
    if isinstance(data, list) and data:
        return sum(c.get("contributions", 0) for c in data)
    commits = _get(f"{base_url}/repos/{owner}/{repo}/commits",
                   token, params={"per_page": 100})
    return len(commits) if isinstance(commits, list) else 0


def _contributor_count(owner: str, repo: str, base_url: str, token: str) -> int:
    url = f"{base_url}/repos/{owner}/{repo}/contributors"
    try:
        s    = _get_session(token)
        resp = s.get(url, params={"per_page": 1, "anon": "true"}, timeout=15)
        if resp.status_code != 200:
            return 0
        link = resp.headers.get("Link", "")
        if "last" in link:
            m = re.search(r'page=(\d+)>; rel="last"', link)
            if m:
                return int(m.group(1))
        return len(resp.json())
    except Exception:
        return 0


def fetch(coin: dict, token: str = "",
          base_url: str = "https://api.github.com") -> Optional[dict]:
    coin_id = coin["coin_id"]
    owner   = coin.get("owner", "")
    repo    = coin.get("repo", "")

    if not owner or not repo:
        logger.info(f"[GitHub] {coin_id}: no repo configured")
        return None

    repo_data = _get(f"{base_url}/repos/{owner}/{repo}", token)
    if not repo_data:
        return None

    return {
        "coin_id":            coin_id,
        "symbol":             coin.get("symbol", ""),
        "owner":              owner,
        "repo":               repo,
        "github_url":         f"https://github.com/{owner}/{repo}",
        "total_commit_count": _total_commits(owner, repo, base_url, token),
        "contributor_count":  _contributor_count(owner, repo, base_url, token),
        "stars":              repo_data.get("stargazers_count", 0),
        "forks":              repo_data.get("forks_count", 0),
        "open_issues":        repo_data.get("open_issues_count", 0),
        "license":            (repo_data.get("license") or {}).get("spdx_id"),
        "last_push_iso":      repo_data.get("pushed_at"),
        "snapshot_time":      datetime.now(timezone.utc).isoformat(),
        "source":             "github_api",
    }
