"""
Abstract base for all GitHub activity sources.

Every source module in sources/ must implement:

    def fetch(coin: dict, token: str = "",
              base_url: str = "https://api.github.com") -> dict | None

Return shape (or None on failure):
{
    coin_id, symbol, owner, repo, github_url,
    total_commit_count,
    contributor_count,
    stars, forks, open_issues,
    license,
    last_push_iso,
    snapshot_time,
    source
}

coins.json entry shape:
{
    "coin_id": "ethereum",
    "symbol": "ETH",
    "source": "github_api",
    "owner": "ethereum",
    "repo": "go-ethereum"
}
"""
