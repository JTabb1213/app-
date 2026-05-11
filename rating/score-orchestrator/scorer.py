"""
Score Orchestrator — Scoring Logic
=====================================
Converts raw collector data into category scores and an automated_score.

Point allocation (75 automated total):
  Security & Transparency   35 pts  — holder diversity
  Tokenomics & Utility      20 pts  — supply structure
  Community & Dev Activity  15 pts  — GitHub delta commits + contributors
  Public Discourse           5 pts  — sentiment + search interest
  ─────────────────────────────────
  Automated total           75 pts
  Manual validation         25 pts  (set by analysts in DB)
  ─────────────────────────────────
  Overall max              100 pts
"""

from typing import Optional


# ── Security & Transparency (35 pts) ──────────────────────────────────────────

def _score_security(holder_data: Optional[dict]) -> dict:
    """
    Score based on holder concentration. None = no data (score 0).

    top_10_pct  : 18 pts — main diversity signal
    top_1_pct   : 12 pts — largest single wallet
    holder_count:  5 pts — breadth of ownership
    """
    MAX = 35

    if not holder_data:
        return {"score": 0, "max": MAX, "metrics": {}, "note": "no data"}

    top_10  = holder_data.get("top_10_pct",   100.0)
    top_1   = holder_data.get("top_1_pct",    100.0)
    count   = holder_data.get("holder_count", 0)

    # top_10_pct (18 pts)
    if   top_10 < 20:  s10 = 18
    elif top_10 < 30:  s10 = 15
    elif top_10 < 40:  s10 = 11
    elif top_10 < 50:  s10 = 7
    elif top_10 < 65:  s10 = 3
    else:              s10 = 0

    # top_1_pct (12 pts)
    if   top_1 < 5:    s1 = 12
    elif top_1 < 10:   s1 = 9
    elif top_1 < 20:   s1 = 6
    elif top_1 < 30:   s1 = 3
    else:              s1 = 0

    # holder_count (5 pts)
    if   count > 100_000: sc = 5
    elif count > 10_000:  sc = 4
    elif count > 1_000:   sc = 3
    elif count > 500:     sc = 2
    elif count > 10:      sc = 1
    else:                 sc = 0

    total = s10 + s1 + sc
    return {
        "score": round(total, 2),
        "max":   MAX,
        "metrics": {
            "top_10_pct":      top_10,
            "top_10_score":    s10,
            "largest_wallet_pct": top_1,
            "largest_wallet_score": s1,
            "holder_count":    count,
            "holder_count_score": sc,
        },
    }


# ── Tokenomics & Utility (20 pts) ─────────────────────────────────────────────

def _score_tokenomics(tokenomics_data: Optional[dict]) -> dict:
    """
    Score based on supply structure. No circulating supply — that's short-term.

    has_max_supply        : 10 pts — capped supply is a positive signal
    inflation_potential   : 10 pts — lower % remaining to issue = less dilution
    """
    MAX = 20

    if not tokenomics_data:
        return {"score": 0, "max": MAX, "metrics": {}, "note": "no data"}

    max_supply   = tokenomics_data.get("max_supply")
    inflation    = tokenomics_data.get("inflation_potential_pct")  # % of max not yet issued

    # has_max_supply (10 pts)
    has_cap = max_supply is not None and max_supply > 0
    scap    = 10 if has_cap else 4  # uncapped gets 4 (not 0 — some valid uses)

    # inflation_potential_pct (10 pts)
    if not has_cap or inflation is None:
        sinfl = 3  # unlimited supply — neutral-ish
    elif inflation < 1:    sinfl = 10  # almost fully issued
    elif inflation < 5:    sinfl = 9
    elif inflation < 10:   sinfl = 8
    elif inflation < 25:   sinfl = 6
    elif inflation < 50:   sinfl = 4
    elif inflation < 75:   sinfl = 2
    else:                  sinfl = 0

    total = scap + sinfl
    return {
        "score": round(total, 2),
        "max":   MAX,
        "metrics": {
            "has_max_supply":           has_cap,
            "has_max_supply_score":     scap,
            "inflation_potential_pct":  inflation,
            "inflation_score":          sinfl,
        },
    }


# ── Community & Dev Activity (15 pts) ─────────────────────────────────────────

def _score_community(
    github_data:       Optional[dict],
    prev_community:    Optional[dict],   # JSONB from last SQL row
) -> dict:
    """
    Score based on recent commit activity and contributor base.

    delta_commits      : 8 pts — commits since last orchestrator run
    contributor_count  : 7 pts — active developer count

    delta_commits is calculated as:
        current total_commit_count − previous total_commit_count stored in DB
    """
    MAX = 15

    if not github_data:
        return {"score": 0, "max": MAX, "metrics": {}, "note": "no repo or fetch failed"}

    curr_total   = github_data.get("total_commit_count", 0)
    contributors = github_data.get("contributor_count", 0)

    # Compute delta_commits
    if prev_community:
        prev_metrics = prev_community.get("metrics", {})
        prev_total   = prev_metrics.get("total_commit_count", 0)
        delta        = max(curr_total - prev_total, 0)
    else:
        delta = curr_total  # first run — treat total as delta

    # delta_commits (8 pts)
    if   delta >= 200: sd = 8
    elif delta >= 100: sd = 7
    elif delta >= 50:  sd = 6
    elif delta >= 20:  sd = 4
    elif delta >= 10:  sd = 2
    elif delta >= 1:   sd = 1
    else:              sd = 0

    # contributor_count (7 pts)
    if   contributors >= 1000: sc = 7
    elif contributors >= 500:  sc = 6
    elif contributors >= 200:  sc = 5
    elif contributors >= 100:  sc = 4
    elif contributors >= 50:   sc = 3
    elif contributors >= 20:   sc = 2
    elif contributors >= 5:    sc = 1
    else:                      sc = 0

    total = sd + sc
    return {
        "score": round(total, 2),
        "max":   MAX,
        "metrics": {
            "total_commit_count":   curr_total,   # stored for next run's delta
            "delta_commits":        delta,
            "delta_commits_score":  sd,
            "contributor_count":    contributors,
            "contributor_score":    sc,
            "github_url":           github_data.get("github_url"),
            "stars":                github_data.get("stars"),
        },
    }


# ── Public Discourse (5 pts) ──────────────────────────────────────────────────

def _score_discourse(discourse_data: Optional[dict]) -> dict:
    """
    Score based on sentiment and search interest.

    social_sentiment : 2.5 pts — Reddit + News VADER (weighted 60/40)
    search_interest  : 2.5 pts — Google Trends 0-100
    """
    MAX = 5

    if not discourse_data:
        return {"score": 2.5, "max": MAX, "metrics": {}, "note": "no data — neutral default"}

    reddit  = discourse_data.get("reddit_compound")
    news    = discourse_data.get("news_compound")
    trends  = discourse_data.get("search_interest")

    # Sentiment (Reddit 60%, News 40%) → 0-1 → scale to 2.5
    parts, weights = [], []
    if reddit is not None:
        parts.append(((reddit + 1) / 2, 0.60))
    if news is not None:
        parts.append(((news + 1) / 2, 0.40))
    if parts:
        tw   = sum(w for _, w in parts)
        sent = sum(v * w for v, w in parts) / tw
    else:
        sent = 0.5  # neutral
    sentiment_score = round(sent * 2.5, 4)

    # Search interest → 0-1 → scale to 2.5
    if trends is not None:
        interest_score = round(min(trends / 100, 1.0) * 2.5, 4)
    else:
        interest_score = 1.25  # neutral default

    total = round(sentiment_score + interest_score, 4)
    return {
        "score": min(total, MAX),
        "max":   MAX,
        "metrics": {
            "reddit_compound":   reddit,
            "news_compound":     news,
            "search_interest":   trends,
            "sentiment_score":   sentiment_score,
            "interest_score":    interest_score,
        },
    }


# ── Risk level ────────────────────────────────────────────────────────────────

def _risk_level(overall: float) -> str:
    if overall >= 80: return "Low"
    if overall >= 60: return "Moderate"
    return "High"


# ── Main entry point ──────────────────────────────────────────────────────────

def calculate(
    coin_id:          str,
    coin_symbol:      str,
    holder_data:      Optional[dict],
    tokenomics_data:  Optional[dict],
    github_data:      Optional[dict],
    discourse_data:   Optional[dict],
    prev_community:   Optional[dict],   # previous community_dev_activity JSONB from SQL
    manual_validation: float = 25.0,
) -> dict:
    """
    Calculate the full CCS score for a single coin.

    Args:
        coin_id, coin_symbol: identity
        holder_data:       raw output from collectors.holder_diversity.fetch()
        tokenomics_data:   raw output from collectors.tokenomics.fetch_batch()
        github_data:       raw output from collectors.github.fetch()
        discourse_data:    raw output from collectors.public_discourse.fetch()
        prev_community:    community_dev_activity JSONB from previous SQL row (for delta)
        manual_validation: analyst score (0-25), read from SQL, default 25

    Returns:
        Full score_row dict ready to write to SQL and Redis.
    """
    sec  = _score_security(holder_data)
    tok  = _score_tokenomics(tokenomics_data)
    com  = _score_community(github_data, prev_community)
    disc = _score_discourse(discourse_data)

    automated = round(sec["score"] + tok["score"] + com["score"] + disc["score"], 2)
    overall   = round(min(automated + manual_validation, 100.0), 2)

    return {
        "coin_id":               coin_id.lower(),
        "coin_symbol":           coin_symbol.upper(),
        "overall_score":         overall,
        "automated_score":       automated,
        "manual_validation":     round(manual_validation, 2),
        "risk_level":            _risk_level(overall),
        "security_transparency": sec,
        "tokenomics_utility":    tok,
        "community_dev_activity": com,
        "public_discourse":      disc,
    }
