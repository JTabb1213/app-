-- =============================================================================
-- price_candles.sql
-- OHLCV candlestick tables for bar chart rendering
--
-- Architecture:
--   A background worker (e.g. candle_builder.py) reads live price snapshots
--   from Redis (rt:coin:<id>) on a timer and writes completed candles here.
--
--   Separate tables per resolution avoids bloat on the most-queried table
--   (1m candles accumulate fastest) and allows different retention policies.
--
-- Retention guidelines (50 coins):
--   price_candles_1m  — keep 90 days  (~6.5M rows)
--   price_candles_5m  — keep 1 year   (~5.3M rows)
--   price_candles_1h  — keep 5 years  (~2.2M rows)
--   price_candles_1d  — keep forever  (~90K rows/year)
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1-minute candles
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS price_candles_1m (
    id          BIGSERIAL   PRIMARY KEY,
    coin_id     TEXT        NOT NULL,               -- e.g. "bitcoin"
    bucket      TIMESTAMPTZ NOT NULL,               -- start of the 1-min window (truncated)
    open        NUMERIC(24, 8) NOT NULL,
    high        NUMERIC(24, 8) NOT NULL,
    low         NUMERIC(24, 8) NOT NULL,
    close       NUMERIC(24, 8) NOT NULL,
    volume      NUMERIC(24, 8) NOT NULL DEFAULT 0,  -- trade volume in base coin units
    exchange_count  SMALLINT NOT NULL DEFAULT 0,    -- how many exchanges contributed
    tick_count  INT         NOT NULL DEFAULT 0,     -- raw price ticks aggregated
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uidx_candles_1m_coin_bucket
    ON price_candles_1m (coin_id, bucket);

CREATE INDEX IF NOT EXISTS idx_candles_1m_bucket
    ON price_candles_1m (bucket DESC);

-- ---------------------------------------------------------------------------
-- 5-minute candles
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS price_candles_5m (
    id          BIGSERIAL   PRIMARY KEY,
    coin_id     TEXT        NOT NULL,
    bucket      TIMESTAMPTZ NOT NULL,
    open        NUMERIC(24, 8) NOT NULL,
    high        NUMERIC(24, 8) NOT NULL,
    low         NUMERIC(24, 8) NOT NULL,
    close       NUMERIC(24, 8) NOT NULL,
    volume      NUMERIC(24, 8) NOT NULL DEFAULT 0,
    exchange_count  SMALLINT NOT NULL DEFAULT 0,
    tick_count  INT         NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uidx_candles_5m_coin_bucket
    ON price_candles_5m (coin_id, bucket);

CREATE INDEX IF NOT EXISTS idx_candles_5m_bucket
    ON price_candles_5m (bucket DESC);

-- ---------------------------------------------------------------------------
-- 1-hour candles
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS price_candles_1h (
    id          BIGSERIAL   PRIMARY KEY,
    coin_id     TEXT        NOT NULL,
    bucket      TIMESTAMPTZ NOT NULL,
    open        NUMERIC(24, 8) NOT NULL,
    high        NUMERIC(24, 8) NOT NULL,
    low         NUMERIC(24, 8) NOT NULL,
    close       NUMERIC(24, 8) NOT NULL,
    volume      NUMERIC(24, 8) NOT NULL DEFAULT 0,
    exchange_count  SMALLINT NOT NULL DEFAULT 0,
    tick_count  INT         NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uidx_candles_1h_coin_bucket
    ON price_candles_1h (coin_id, bucket);

CREATE INDEX IF NOT EXISTS idx_candles_1h_bucket
    ON price_candles_1h (bucket DESC);

-- ---------------------------------------------------------------------------
-- 1-day candles
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS price_candles_1d (
    id          BIGSERIAL   PRIMARY KEY,
    coin_id     TEXT        NOT NULL,
    bucket      DATE        NOT NULL,               -- just the date (UTC)
    open        NUMERIC(24, 8) NOT NULL,
    high        NUMERIC(24, 8) NOT NULL,
    low         NUMERIC(24, 8) NOT NULL,
    close       NUMERIC(24, 8) NOT NULL,
    volume      NUMERIC(24, 8) NOT NULL DEFAULT 0,
    exchange_count  SMALLINT NOT NULL DEFAULT 0,
    tick_count  INT         NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uidx_candles_1d_coin_bucket
    ON price_candles_1d (coin_id, bucket);

CREATE INDEX IF NOT EXISTS idx_candles_1d_bucket
    ON price_candles_1d (bucket DESC);

-- ---------------------------------------------------------------------------
-- Retention helper views (optional — useful for monitoring table size)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW candle_row_counts AS
SELECT 'price_candles_1m' AS tbl, COUNT(*) AS rows FROM price_candles_1m
UNION ALL
SELECT 'price_candles_5m', COUNT(*) FROM price_candles_5m
UNION ALL
SELECT 'price_candles_1h', COUNT(*) FROM price_candles_1h
UNION ALL
SELECT 'price_candles_1d', COUNT(*) FROM price_candles_1d;

-- ---------------------------------------------------------------------------
-- Retention cleanup queries (run via cron or a scheduled task)
-- Adjust intervals to match your retention policy above.
-- ---------------------------------------------------------------------------
-- DELETE FROM price_candles_1m WHERE bucket < NOW() - INTERVAL '90 days';
-- DELETE FROM price_candles_5m WHERE bucket < NOW() - INTERVAL '1 year';
-- DELETE FROM price_candles_1h WHERE bucket < NOW() - INTERVAL '5 years';
-- (1d candles — keep forever, no cleanup needed)
