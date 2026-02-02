def score_stars(stars):
    """Score based on GitHub stars (0-100)"""
    if stars >= 50000:
        return 100
    elif stars >= 10000:
        return 90
    elif stars >= 5000:
        return 80
    elif stars >= 1000:
        return 70
    elif stars >= 500:
        return 60
    elif stars >= 100:
        return 50
    elif stars >= 10:
        return 40
    else:
        return max(0, stars)

def score_commits(commits_year):
    """Score based on commits in the last year (0-100)"""
    if commits_year >= 5000:
        return 100
    elif commits_year >= 2000:
        return 90
    elif commits_year >= 1000:
        return 80
    elif commits_year >= 500:
        return 70
    elif commits_year >= 200:
        return 60
    elif commits_year >= 50:
        return 50
    elif commits_year >= 10:
        return 40
    else:
        return max(0, commits_year * 2)

def score_contributors(contributors):
    """Score based on number of contributors (0-100)"""
    if contributors >= 1000:
        return 100
    elif contributors >= 500:
        return 90
    elif contributors >= 200:
        return 80
    elif contributors >= 100:
        return 70
    elif contributors >= 50:
        return 60
    elif contributors >= 20:
        return 50
    elif contributors >= 5:
        return 40
    else:
        return max(0, contributors * 5)

def calculate_github_score(stars, commits_year, contributors):
    """
    Calculate overall GitHub activity score using weighted average.
    Weights: stars (40%), commits (40%), contributors (20%)
    """
    stars_score = score_stars(stars)
    commits_score = score_commits(commits_year)
    contributors_score = score_contributors(contributors)
    
    final_score = (
        stars_score * 0.40 +
        commits_score * 0.40 +
        contributors_score * 0.20
    )
    
    return round(final_score, 2)
