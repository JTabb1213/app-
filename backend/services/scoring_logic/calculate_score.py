def score_market_cap(market_cap):
    """Score based on market cap (0-100)"""
    if market_cap is None or market_cap == 0:
        return 0
    
    # Tier-based scoring
    if market_cap >= 1_000_000_000_000:  # $1T+
        return 100
    elif market_cap >= 100_000_000_000:  # $100B+
        return 95
    elif market_cap >= 10_000_000_000:   # $10B+
        return 85
    elif market_cap >= 1_000_000_000:    # $1B+
        return 75
    elif market_cap >= 100_000_000:      # $100M+
        return 60
    elif market_cap >= 10_000_000:       # $10M+
        return 45
    else:
        return 30

def score_volume(volume_24h, market_cap):
    """Score based on 24h volume relative to market cap (0-100)"""
    if market_cap is None or market_cap == 0 or volume_24h is None or volume_24h == 0:
        return 0
    
    volume_ratio = volume_24h / market_cap
    
    if volume_ratio >= 0.5:      # 50%+ volume/market cap
        return 100
    elif volume_ratio >= 0.25:   # 25%+ 
        return 85
    elif volume_ratio >= 0.10:   # 10%+
        return 70
    elif volume_ratio >= 0.05:   # 5%+
        return 55
    elif volume_ratio >= 0.01:   # 1%+
        return 40
    else:
        return 20

def score_holder_diversity(top_holder_percentage):
    """Score based on holder diversity (0-100, lower concentration = higher score)"""
    if top_holder_percentage is None:
        return 50
    
    concentration = top_holder_percentage
    
    if concentration <= 0.05:    # Top holder < 5%
        return 100
    elif concentration <= 0.10:  # < 10%
        return 90
    elif concentration <= 0.15:  # < 15%
        return 80
    elif concentration <= 0.20:  # < 20%
        return 70
    elif concentration <= 0.30:  # < 30%
        return 60
    elif concentration <= 0.50:  # < 50%
        return 40
    else:
        return 20

def calculate_final_score(market_cap_score, volume_score, holder_diversity_score, github_score):
    """
    Calculate final weighted score.
    Weights: market_cap (25%), volume (15%), holder_diversity (25%), github_activity (35%)
    """
    final_score = (
        market_cap_score * 0.25 +
        volume_score * 0.15 +
        holder_diversity_score * 0.25 +
        github_score * 0.35
    )
    
    return round(final_score, 2)
