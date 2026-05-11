"""
GitHub Activity Fetcher
=======================
Fetches commit count (total, for delta calculation), contributor count,
and last push date from the GitHub REST API.

The commit delta (commits since last run) is calculated in main.py by
comparing the current total_commit_count to the previously stored value
in SQL. This gives "commits in the last 7 days" without any date filtering.

GitHub token is optional but strongly recommended:
  - Unauthenticated: 60 req/hour
  - Authenticated:   5,000 req/hour
"""

import logging
import re
import time
from datetime import datetime, timezone
from typing import Optional

import requests

import config

logger = logging.getLogger(__name__)

_SESSION = requests.Session()
_SESSION.headers.update({
    "Accept": "application/vnd.github+json",
    **({"Authorization": f"Bearer {config.GITHUB_TOKEN}"} if config.GITHUB_TOKEN else {}),
})


def _get(url: str, params: dict | None = None) -> dict | list | None:
    """Make a GitHub API GET with automatic rate-limit handling."""
    try:
        resp = _SESSION.get(url, params=params, timeout=15)

        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait  = max(reset - int(time.time()), 1)
            logger.warning(f"GitHub rate limited — sleeping {wait}s")
            time.sleep(wait)
            resp = _SESSION.get(url, params=params, timeout=15)

        if resp.status_code == 404:
            logger.warning(f"GitHub 404: {url}")
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        logger.error(f"GitHub request error {url}: {exc}")
        return None


def _fetch_total_commits(owner: str, repo: str) -> int:
    """
    Return total commit count by summing contributions from /contributors.
    This is the number we store — delta between runs = commits since last run.
    Falls back to counting the first page of /commits if contributors returns empty.
    """
    data = _get(
        f"{config.GITHUB_API_BASE}/repos/{owner}/{repo}/contributors",
        params={"per_page": 100},
    )
    if isinstance(data, list) and data:
        return sum(c.get("contributions", 0) for c in data)

    # Fallback — not perfectly accurate for large repos but consistent
    commits = _get(
        f"{config.GITHUB_API_BASE}/repos/{owner}/{repo}/commits",
        params={"per_page": 100},
    )
    return len(commits) if isinstance(commits, list) else 0


def _fetch_contributor_count(owner: str, repo: str) -> int:
    """
    Use the Link header pagination trick — one request, any repo size.
    """
    url = f"{config.GITHUB_API_BASE}/repos/{owner}/{repo}/contributors"
    try:
        resp = _SESSION.get(url, params={"per_page": 1, "anon": "true"}, timeout=15)
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


def fetch_snapshot(coin: dict) -> Optional[dict]:
    """
    Fetch all GitHub metrics for a single coin and return a normalised snapshot.

    Returns None if the coin has no configured repo or the repo is unreachable.
    """
    coin_id = coin["coin_id"]
    owner   = coin.get("owner", "")
    repo    = coin.get("repo", "")

    if not owner or not repo:
        logger.info(f"[GitHub] {coin_id}: no repo configured — skipping")
        return None

    logger.info(f"[GitHub] Fetching {owner}/{repo} …")

    repo_data = _get(f"{config.GITHUB_API_BASE}/repos/{owner}/{repo}")
    if not repo_data:
        return None

    total_commits    = _fetch_total_commits(owner, repo)
    contributor_count = _fetch_contributor_count(owner, repo)
    pushed_at        = repo_data.get("pushed_at")

    return {
        "coin_id":            coin_id,
        "symbol":             coin["symbol"],
        "owner":              owner,
        "repo":               repo,
        "github_url":         f"https://github.com/{owner}/{repo}",
        # Stored to compute delta (commits since last run) in main.py
        "total_commit_count": total_commits,
        # Contributor count — slowly changing, used directly in score
        "contributor_count":  contributor_count,
        # Stars / forks — useful context, not scored
        "stars":              repo_data.get("stargazers_count", 0),
        "forks":              repo_data.get("forks_count", 0),
        "open_issues":        repo_data.get("open_issues_count", 0),
        "license":            (repo_data.get("license") or {}).get("spdx_id"),
        "last_push_iso":      pushed_at,
        "snapshot_time":      datetime.now(timezone.utc).isoformat(),
        "source":             "GitHub",
    }
