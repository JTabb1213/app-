"""
fetchers/trends.py
==================
Fetches Google Trends relative search interest for a coin using pytrends.
Returns an average interest score (0-100) over the configured timeframe.

No API key required.
"""

import time
from pytrends.request import TrendReq
from pytrends.exceptions import TooManyRequestsError

import config

_pytrends = TrendReq(hl="en-US", tz=0)


def fetch_interest(coin: dict) -> dict:
    """
    Fetch Google Trends search interest for a coin.
    Uses the first search query from coin config.

    Returns:
        {
            "avg_interest": float | None,  # 0-100
            "peak_interest": float | None, # highest value in window
            "source": "google_trends",
        }
    """
    # Use the most recognisable query (first entry)
    keyword = coin["search_queries"][0]

    try:
        _pytrends.build_payload([keyword], timeframe=config.TRENDS_TIMEFRAME, geo="")
        df = _pytrends.interest_over_time()
    except TooManyRequestsError:
        time.sleep(60)
        try:
            _pytrends.build_payload([keyword], timeframe=config.TRENDS_TIMEFRAME, geo="")
            df = _pytrends.interest_over_time()
        except Exception:
            return {"avg_interest": None, "peak_interest": None, "source": "google_trends", "error": "rate limited"}
    except Exception as e:
        return {"avg_interest": None, "peak_interest": None, "source": "google_trends", "error": str(e)}

    if df is None or df.empty or keyword not in df.columns:
        return {"avg_interest": None, "peak_interest": None, "source": "google_trends"}

    series = df[keyword]
    avg    = round(float(series.mean()), 2)
    peak   = round(float(series.max()), 2)

    return {
        "avg_interest":  avg,
        "peak_interest": peak,
        "source":        "google_trends",
    }
