"""
scorer.py
=========
Converts raw discourse signals into a 0-2 score for the CCS rating system.

Inputs:
  - reddit_compound  : VADER avg compound from Reddit  (-1.0 to +1.0)
  - news_compound    : VADER avg compound from NewsAPI (-1.0 to +1.0)
  - search_interest  : Google Trends avg interest      (0-100)

Output:
  - social_sentiment_score : 0-1  (Reddit + News combined)
  - search_interest_score  : 0-1  (Google Trends)
  - discourse_score        : 0-2  (total for CCS)
"""


def _score_sentiment(reddit_compound: float | None, news_compound: float | None) -> float:
    """
    Combine Reddit and News VADER compound scores into a 0-1 sentiment score.

    Each compound is -1 to +1. Map to 0-1 then average available sources.
    Weights: Reddit 60%, News 40% (Reddit is more real-time community signal).
    """
    scores = []

    if reddit_compound is not None:
        scores.append(((reddit_compound + 1) / 2, 0.60))

    if news_compound is not None:
        scores.append(((news_compound + 1) / 2, 0.40))

    if not scores:
        return 0.5  # neutral default when no data

    total_weight = sum(w for _, w in scores)
    weighted_sum = sum(v * w for v, w in scores)
    return round(weighted_sum / total_weight, 4)


def _score_search_interest(avg_interest: float | None) -> float:
    """
    Convert Google Trends interest (0-100) to a 0-1 score.
    Returns 0.5 (neutral) when data is unavailable.
    """
    if avg_interest is None:
        return 0.5
    return round(max(0.0, min(1.0, avg_interest / 100)), 4)


def calculate_discourse_score(
    reddit_compound: float | None,
    news_compound: float | None,
    search_interest: float | None,
) -> dict:
    """
    Calculate the total public discourse score out of 2 points.

    Score breakdown:
      - Social Sentiment (Reddit + News) : 0-1
      - Search Interest (Google Trends)  : 0-1
      ─────────────────────────────────────────
      Total                              : 0-2

    Returns a dict with individual and total scores.
    """
    sentiment_score = _score_sentiment(reddit_compound, news_compound)
    interest_score  = _score_search_interest(search_interest)
    total           = round(sentiment_score + interest_score, 4)

    return {
        "score":              total,          # 0-2 (used in CCS)
        "max":                2,
        "social_sentiment":   round(sentiment_score, 4),   # 0-1
        "search_interest":    round(interest_score, 4),    # 0-1
    }
