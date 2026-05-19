"""
Tokenomics collector — abstract base.

Every source in sources/ must implement:

    def fetch(coin: dict, api_key: str = "") -> dict | None

Return shape (or None on failure):
{
    coin_id, name, symbol,
    max_supply,
    total_supply,
    inflation_potential_pct,
    snapshot_time,
    source
}

coins.json entry shape:
{
    "coin_id": "bitcoin",
    "symbol": "BTC",
    "source": "coingecko"
}
"""
