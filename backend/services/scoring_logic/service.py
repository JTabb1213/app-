from services.data import data_service
from services.apis import github
from services.scoring_logic import calculate_score
from services.scoring_logic import github_score


def get_score(coin_id):
    """
    Gather multiple metrics from APIs, compute individual factor scores,
    combine them using weighted averaging, and return detailed breakdown.
    """
    try:
        # 1. Fetch raw coin data using unified service (with automatic fallback)
        data = data_service.get_coin_data(coin_id)
    except Exception as e:
        raise Exception(f"Error fetching coin data: {str(e)}")

    # 2. Extract key metrics
    market_cap = data.get("market_data", {}).get("market_cap", {}).get("usd") or 0
    volume_24h = data.get("market_data", {}).get("total_volume", {}).get("usd") or 0
    
    # Top holder percentage (if available from CoinGecko)
    # Note: CoinGecko doesn't always provide this; we'll estimate from market concentration
    # For now, use a default neutral value (we can enhance later with blockchain data)
    top_holder_percentage = 0.15  # Placeholder; refine with on-chain data later

    # 3. Score individual factors (each returns 0-100)
    market_cap_score = calculate_score.score_market_cap(market_cap)
    volume_score = calculate_score.score_volume(volume_24h, market_cap)
    holder_diversity_score = calculate_score.score_holder_diversity(top_holder_percentage)

    # 4. Fetch GitHub metrics
    github_metrics = None
    github_activity_score = 0  # Default if repo not found
    
    # Try to get repo from mapping first
    repo_info = github.get_repo_for_coin(coin_id)
    if not repo_info:
        # If not in mapping, try to extract from CoinGecko data
        github_repos = data.get("links", {}).get("repos_url", {}).get("github", [])
        if github_repos:
            github_url = github_repos[0]  # Get the first (main) repository
            repo_info = github.get_repo_for_coin(coin_id, github_url)
    
    if repo_info:
        owner, repo = repo_info
        github_metrics = github.get_github_metrics(owner, repo)
        if github_metrics:
            github_activity_score = github_score.calculate_github_score(
                stars=github_metrics.get("stars", 0),
                commits_year=github_metrics.get("commits_year", 0),
                contributors=github_metrics.get("contributors", 0),
            )

    # 5. Compute final weighted score
    final_score = calculate_score.calculate_final_score(
        market_cap_score=market_cap_score,
        volume_score=volume_score,
        holder_diversity_score=holder_diversity_score,
        github_score=github_activity_score,
    )

    # 6. Return detailed breakdown
    result = {
        "coin_id": coin_id,
        "score": final_score,
        "breakdown": {
            "market_cap": {
                "value": market_cap,
                "score": market_cap_score,
                "weight": 0.25,
            },
            "volume_24h": {
                "value": volume_24h,
                "score": volume_score,
                "weight": 0.15,
            },
            "holder_diversity": {
                "value": top_holder_percentage,
                "score": holder_diversity_score,
                "weight": 0.25,
            },
            "github_activity": {
                "score": github_activity_score,
                "weight": 0.35,
                "metrics": github_metrics if github_metrics else {},
            },
        },
    }
    
    return result
