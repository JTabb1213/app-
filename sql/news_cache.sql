-- News cache table
-- Stores the latest 4 Google News articles per coin.
-- Refreshed every 1h by the news service (on-demand cache-miss fetch).

CREATE TABLE IF NOT EXISTS news_cache (
    coin_id    TEXT        PRIMARY KEY,
    articles   JSONB       NOT NULL DEFAULT '[]',
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
