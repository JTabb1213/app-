"""
Public Discourse collector — abstract base.

Every source in sources/ must implement:

    def fetch(coin: dict, newsapi_key: str = "") -> dict | None

Return shape (or None on failure):
{
    coin_id, symbol,
    reddit_compound,
    reddit_post_count,
    news_compound,
    news_article_count,
    search_interest,
    snapshot_time,
    source
}

coins.json entry shape:
{
    "coin_id": "bitcoin",
    "symbol": "BTC",
    "source": "reddit_news_trends",
    "subreddits": ["Bitcoin", "CryptoCurrency"],
    "search_queries": ["Bitcoin", "BTC"]
}
"""
