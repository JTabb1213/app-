"""
test_github_activity.py
=======================
Fetches GitHub activity metrics for every coin defined in coins.json and
prints a structured report.

Metrics collected:
  - GitHub Activity  : commit frequency (commits in the last ~year)
  - Contributors     : active developer count
  - Last Commit      : date of most recent push to the repo

Uses the public GitHub REST API (no auth token required, but rate-limited to
60 req/hour unauthenticated). Set GITHUB_TOKEN in your environment or .env
to raise the limit to 5,000 req/hour.

Install:
    pip install requests python-dotenv

Usage:
    python3 test_github_activity.py
    -- OR with token --
    GITHUB_TOKEN=ghp_... python3 test_github_activity.py
"""

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── Env loading ────────────────────────────────────────────────────────────────
root_env = Path(__file__).resolve().parents[2] / ".env"
if root_env.exists():
    load_dotenv(root_env, override=False)

GITHUB_TOKEN    = os.getenv("GITHUB_TOKEN", "")
GITHUB_API_BASE = "https://api.github.com"

HEADERS = {"Accept": "application/vnd.github+json"}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"

COINS_FILE = Path(__file__).parent / "coins.json"


# ── API helpers ────────────────────────────────────────────────────────────────

def _get(url: str, params: dict | None = None) -> dict | list | None:
    """Make a GitHub API GET request, handling rate limits gracefully."""
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=10)

        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait  = max(reset - int(time.time()), 1)
            print(f"  ⚠ Rate limited — sleeping {wait}s")
            time.sleep(wait)
            resp = requests.get(url, headers=HEADERS, params=params, timeout=10)

        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  ✗ Request failed: {e}")
        return None


def fetch_repo(owner: str, repo: str) -> dict | None:
    """Fetch repository metadata (stars, forks, last push, etc.)."""
    return _get(f"{GITHUB_API_BASE}/repos/{owner}/{repo}")


def fetch_commit_count(owner: str, repo: str) -> int:
    """
    Estimate commit count using the contributors-stats endpoint.
    Falls back to fetching the first page of commits if stats are unavailable.
    """
    # Try contributors stats (total commits per contributor)
    stats = _get(f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contributors",
                 params={"per_page": 100})
    if isinstance(stats, list) and stats:
        return sum(c.get("contributions", 0) for c in stats)

    # Fallback: count commits on first page (max 100, not the full history)
    commits = _get(f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits",
                   params={"per_page": 100})
    if isinstance(commits, list):
        return len(commits)
    return 0


def fetch_contributor_count(owner: str, repo: str) -> int:
    """
    Fetch total contributor count using the Link header pagination trick.
    One API call regardless of contributor count.
    """
    url  = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contributors"
    try:
        resp = requests.get(url, headers=HEADERS, params={"per_page": 1, "anon": "true"}, timeout=10)
        if resp.status_code != 200:
            return 0
        link = resp.headers.get("Link", "")
        if "last" in link:
            match = re.search(r'page=(\d+)>; rel="last"', link)
            if match:
                return int(match.group(1))
        return len(resp.json())
    except Exception:
        return 0


def _days_ago(iso_date: str | None) -> str:
    """Convert an ISO date string to a human-readable '12 days ago' string."""
    if not iso_date:
        return "unknown"
    try:
        dt   = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        days = (datetime.now(timezone.utc) - dt).days
        if days == 0:
            return "today"
        if days == 1:
            return "yesterday"
        return f"{days} days ago"
    except Exception:
        return iso_date[:10]


# ── Per-coin processing ────────────────────────────────────────────────────────

def process_coin(coin: dict) -> dict:
    coin_id = coin["coin_id"]
    owner   = coin.get("owner", "")
    repo    = coin.get("repo", "")

    if not owner or not repo:
        return {
            "coin_id":         coin_id,
            "symbol":          coin["symbol"],
            "status":          "no_repo",
            "note":            coin.get("note", "No GitHub repository configured"),
        }

    print(f"\n  Fetching {owner}/{repo}…")

    repo_data         = fetch_repo(owner, repo)
    if not repo_data:
        return {"coin_id": coin_id, "symbol": coin["symbol"], "status": "not_found",
                "owner": owner, "repo": repo}

    last_commit_iso   = repo_data.get("pushed_at")
    stars             = repo_data.get("stargazers_count", 0)
    forks             = repo_data.get("forks_count", 0)
    open_issues       = repo_data.get("open_issues_count", 0)
    license_name      = (repo_data.get("license") or {}).get("name")

    commit_count      = fetch_commit_count(owner, repo)
    contributor_count = fetch_contributor_count(owner, repo)

    return {
        "coin_id":          coin_id,
        "symbol":           coin["symbol"],
        "status":           "ok",
        "github_url":       f"https://github.com/{owner}/{repo}",

        # The three metrics needed for the CCS score
        "github_activity": {
            "commit_count": commit_count,
            "label":        f"{commit_count:,} total commits",
        },
        "contributors": {
            "count":  contributor_count,
            "label":  f"{contributor_count:,} contributors",
        },
        "last_commit": {
            "iso":   last_commit_iso,
            "human": _days_ago(last_commit_iso),
        },

        # Bonus context
        "stars":       stars,
        "forks":       forks,
        "open_issues": open_issues,
        "license":     license_name,
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    with open(COINS_FILE) as f:
        coins = json.load(f)

    auth_status = "authenticated" if GITHUB_TOKEN else "unauthenticated (60 req/hr limit)"
    print("=" * 65)
    print(f"GitHub Activity Fetcher  —  {len(coins)} coins")
    print(f"Auth: {auth_status}")
    print("=" * 65)

    results  = []
    ok_count = 0

    for coin in coins:
        print(f"\n── {coin['symbol']} ({coin['coin_id']}) {'─' * 40}")
        result = process_coin(coin)
        results.append(result)

        if result["status"] == "ok":
            ok_count += 1
            print(f"  ✓ {result['github_url']}")
            print(f"    GitHub Activity : {result['github_activity']['label']}")
            print(f"    Contributors    : {result['contributors']['label']}")
            print(f"    Last Commit     : {result['last_commit']['human']}  ({result['last_commit']['iso'][:10] if result['last_commit']['iso'] else 'N/A'})")
            print(f"    Stars           : {result['stars']:,}")
            print(f"    License         : {result['license'] or 'not specified'}")
        elif result["status"] == "no_repo":
            print(f"  — {result.get('note', 'No repo')}")
        else:
            print(f"  ✗ Repo not found: {result.get('owner')}/{result.get('repo')}")

        #time.sleep(0.5)   # stay well under rate limits

    print("\n" + "=" * 65)
    print(f"Done. Fetched {ok_count}/{len(coins)} repos successfully.")

    # Dump full JSON for inspection
    out_file = Path(__file__).parent / "github_results.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Full results saved → {out_file}")


if __name__ == "__main__":
    main()
