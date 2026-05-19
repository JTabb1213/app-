-- Market data snapshot table
-- Stores the latest CoinGecko snapshot per coin.
-- Refreshed by the market-collector service (default every 6 h).

CREATE TABLE IF NOT EXISTS market_data (
    coin_id              TEXT        PRIMARY KEY,
    price_usd            NUMERIC,
    market_cap           NUMERIC,
    volume_24h           NUMERIC,
    price_change_24h     NUMERIC,
    price_change_pct_24h NUMERIC,
    circulating_supply   NUMERIC,
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_market_data_updated ON market_data (updated_at DESC);
