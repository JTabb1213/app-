import requests
import re

GITHUB_API_BASE = "https://api.github.com"

def extract_owner_repo_from_url(github_url):
    """
    Extract owner and repo from GitHub URL.
    """
    if not github_url:
        return None
    
    url = github_url.replace("https://", "").replace("http://", "").rstrip("/")
    parts = url.split("/")
    if len(parts) >= 3 and "github.com" in parts[0]:
        return (parts[1], parts[2])
    
    return None

def fetch_repo_data(owner, repo):
    """
    Fetch repository data from GitHub API.
    """
    try:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise Exception(f"GitHub API error: {response.status_code}")
        
        return response.json()
    except Exception as e:
        return None

def get_commit_count_last_year(owner, repo):
    """
    Fetch commit count for the last year.
    """
    try:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits"
        response = requests.get(url, params={"per_page": 100}, timeout=5)
        if response.status_code == 200:
            return len(response.json())
        return 0
    except Exception as e:
        return 0

def get_contributors(owner, repo):
    """
    Fetch number of contributors.
    """
    try:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contributors"
        response = requests.get(url, params={"per_page": 1}, timeout=5)
        
        if response.status_code == 200:
            link_header = response.headers.get("Link", "")
            if "last" in link_header:
                match = re.search(r'page=(\d+)>; rel="last"', link_header)
                if match:
                    return int(match.group(1))
            return len(response.json())
        return 0
    except Exception as e:
        return 0

def get_github_metrics(owner, repo):
    """
    Fetch all relevant GitHub metrics for a crypto project.
    """
    repo_data = fetch_repo_data(owner, repo)
    if not repo_data:
        return None
    
    metrics = {
        "url": f"https://github.com/{owner}/{repo}",
        "stars": repo_data.get("stargazers_count", 0),
        "forks": repo_data.get("forks_count", 0),
        "watchers": repo_data.get("watchers_count", 0),
        "open_issues": repo_data.get("open_issues_count", 0),
        "created_at": repo_data.get("created_at"),
        "last_commit": repo_data.get("pushed_at"),
        "license": repo_data.get("license", {}).get("name") if repo_data.get("license") else None,
        "is_fork": repo_data.get("fork", False),
    }
    
    metrics["commits_year"] = get_commit_count_last_year(owner, repo)
    metrics["contributors"] = get_contributors(owner, repo)
    
    return metrics

GITHUB_REPO_MAPPING = {
    "bitcoin": ("bitcoin", "bitcoin"),
    "ethereum": ("ethereum", "go-ethereum"),
    "cardano": ("input-output-hk", "cardano-sl"),
    "solana": ("solana-labs", "solana"),
    "polkadot": ("paritytech", "polkadot"),
    "ripple": ("XRPLF", "rippled"),
    "dogecoin": ("dogecoin", "dogecoin"),
    "litecoin": ("litecoin-project", "litecoin"),
    "monero": ("monero-project", "monero"),
    "zcash": ("zcash", "zcash"),
}

def get_repo_for_coin(coin_id, github_url=None):
    """
    Get GitHub repo for a coin.
    First checks fallback mapping, then tries to extract from provided GitHub URL.
    """
    coin_id_lower = coin_id.lower()
    
    # Check fallback mapping first
    if coin_id_lower in GITHUB_REPO_MAPPING:
        return GITHUB_REPO_MAPPING[coin_id_lower]
    
    # If a GitHub URL is provided, extract owner/repo from it
    if github_url:
        extracted = extract_owner_repo_from_url(github_url)
        if extracted:
            return extracted
    
    return None
