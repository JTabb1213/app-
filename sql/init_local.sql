-- =============================================================================
-- Local Dev — Database Initialisation Script
-- =============================================================================
-- This file is auto-run by the postgres Docker container on first start.
-- It creates every table the app needs so you can test locally without
-- touching the production Supabase database.
--
-- Run order matters — coins must exist before anything references coin_id.
-- =============================================================================

-- ── 1. Core coins table ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS coins (
  id                 TEXT PRIMARY KEY,
  symbol             TEXT NOT NULL,
  name               TEXT NOT NULL,
  image_url          TEXT,
  github_url         TEXT,
  market_cap_rank    INTEGER,
  circulating_supply NUMERIC,
  total_supply       NUMERIC,
  max_supply         NUMERIC,
  fully_diluted_valuation NUMERIC,
  ath                NUMERIC,
  ath_date           TIMESTAMPTZ,
  atl                NUMERIC,
  atl_date           TIMESTAMPTZ,
  description        TEXT,
  rating_score       NUMERIC(4, 2),
  rating_notes       TEXT,
  review_count       INTEGER,
  is_featured        BOOLEAN DEFAULT FALSE,
  diversity_method   TEXT NOT NULL DEFAULT 'token_holders',
  created_at         TIMESTAMPTZ DEFAULT NOW(),
  updated_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_coins_market_cap_rank ON coins(market_cap_rank);
CREATE INDEX IF NOT EXISTS idx_coins_symbol ON coins(symbol);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_set_updated_at ON coins;
CREATE TRIGGER trg_set_updated_at
BEFORE UPDATE ON coins
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ── 2. Rating scores (main output of the score orchestrator) ─────────────────
CREATE TABLE IF NOT EXISTS rating_scores (
    coin_id                TEXT         PRIMARY KEY,
    coin_symbol            TEXT         NOT NULL,
    overall_score          NUMERIC(5,2) NOT NULL CHECK (overall_score   BETWEEN 0 AND 100),
    automated_score        NUMERIC(5,2) NOT NULL CHECK (automated_score BETWEEN 0 AND 75),
    manual_validation      NUMERIC(5,2) NOT NULL DEFAULT 25 CHECK (manual_validation BETWEEN 0 AND 25),
    risk_level             TEXT         CHECK (risk_level IN ('Low','Moderate','High')),
    review_status          TEXT         NOT NULL DEFAULT 'pending'
                                        CHECK (review_status IN ('pending','complete','archived')),
    security_transparency  JSONB        NOT NULL DEFAULT '{}',
    tokenomics_utility     JSONB        NOT NULL DEFAULT '{}',
    community_dev_activity JSONB        NOT NULL DEFAULT '{}',
    public_discourse       JSONB        NOT NULL DEFAULT '{}',
    score_history          JSONB        NOT NULL DEFAULT '[]',
    last_computed_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rating_overall ON rating_scores(overall_score DESC);
CREATE INDEX IF NOT EXISTS idx_rating_risk    ON rating_scores(risk_level);
CREATE INDEX IF NOT EXISTS idx_rating_status  ON rating_scores(review_status);

CREATE OR REPLACE FUNCTION fn_append_score_history()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.overall_score IS DISTINCT FROM NEW.overall_score THEN
        NEW.score_history = (
            SELECT jsonb_agg(entry)
            FROM (
                SELECT entry FROM jsonb_array_elements(OLD.score_history) AS entry
                UNION ALL
                SELECT jsonb_build_object(
                    'score', OLD.overall_score,
                    'date',  to_char(NOW(), 'YYYY-MM-DD')
                )
                ORDER BY (entry->>'date') DESC
                LIMIT 52
            ) sub
        );
    END IF;
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_rating_updated_at ON rating_scores;
DROP TRIGGER IF EXISTS trg_score_history     ON rating_scores;
CREATE TRIGGER trg_score_history
BEFORE UPDATE ON rating_scores
FOR EACH ROW EXECUTE FUNCTION fn_append_score_history();

-- ── 3. Decentralization risk snapshots ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS decentralization_snapshots (
  id                   SERIAL PRIMARY KEY,
  coin_id              TEXT NOT NULL,
  diversity_method     TEXT NOT NULL DEFAULT 'token_holders',
  chain                TEXT,
  contract_address     TEXT,
  snapshot_time        TIMESTAMPTZ NOT NULL,
  source               TEXT NOT NULL,
  holder_count         INTEGER,
  top_1_pct            REAL,
  top_10_pct           REAL,
  top_100_pct          REAL,
  gini_coefficient     REAL,
  hhi                  REAL,
  nakamoto_coefficient INTEGER,
  insider_pct          REAL,
  circulating_ratio    REAL,
  risk_flags           TEXT[],
  top_holders_json     JSONB,
  created_at           TIMESTAMPTZ DEFAULT NOW(),
  refreshed_at         TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT unique_coin_latest UNIQUE (coin_id)
);

CREATE INDEX IF NOT EXISTS idx_decentral_coin_id       ON decentralization_snapshots(coin_id);
CREATE INDEX IF NOT EXISTS idx_decentral_method        ON decentralization_snapshots(diversity_method);
CREATE INDEX IF NOT EXISTS idx_decentral_snapshot_time ON decentralization_snapshots(snapshot_time DESC);

CREATE TABLE IF NOT EXISTS decentralization_snapshots_history (
  id                   SERIAL PRIMARY KEY,
  coin_id              TEXT NOT NULL,
  diversity_method     TEXT NOT NULL DEFAULT 'token_holders',
  chain                TEXT,
  contract_address     TEXT,
  snapshot_time        TIMESTAMPTZ NOT NULL,
  source               TEXT NOT NULL,
  holder_count         INTEGER,
  top_1_pct            REAL,
  top_10_pct           REAL,
  top_100_pct          REAL,
  gini_coefficient     REAL,
  hhi                  REAL,
  nakamoto_coefficient INTEGER,
  insider_pct          REAL,
  circulating_ratio    REAL,
  risk_flags           TEXT[],
  top_holders_json     JSONB,
  created_at           TIMESTAMPTZ DEFAULT NOW(),
  refreshed_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_decentral_hist_coin_time ON decentralization_snapshots_history(coin_id, snapshot_time DESC);

CREATE OR REPLACE FUNCTION archive_decentralization_snapshot()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'UPDATE' THEN
    INSERT INTO decentralization_snapshots_history (
      coin_id, diversity_method, chain, contract_address,
      snapshot_time, source,
      holder_count, top_1_pct, top_10_pct, top_100_pct,
      gini_coefficient, hhi, nakamoto_coefficient,
      insider_pct, circulating_ratio, risk_flags,
      top_holders_json, created_at, refreshed_at
    ) VALUES (
      OLD.coin_id, OLD.diversity_method, OLD.chain, OLD.contract_address,
      OLD.snapshot_time, OLD.source,
      OLD.holder_count, OLD.top_1_pct, OLD.top_10_pct, OLD.top_100_pct,
      OLD.gini_coefficient, OLD.hhi, OLD.nakamoto_coefficient,
      OLD.insider_pct, OLD.circulating_ratio, OLD.risk_flags,
      OLD.top_holders_json, OLD.created_at, OLD.refreshed_at
    );
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_archive_decentralization_snapshot ON decentralization_snapshots;
CREATE TRIGGER trg_archive_decentralization_snapshot
BEFORE UPDATE ON decentralization_snapshots
FOR EACH ROW EXECUTE FUNCTION archive_decentralization_snapshot();

-- ── 4. Market data ────────────────────────────────────────────────────────────
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

-- ── 5. News cache ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS news_cache (
  coin_id    TEXT        PRIMARY KEY,
  articles   JSONB       NOT NULL DEFAULT '[]',
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── 6. Price candles (one table per resolution) ─────────────────────────────
CREATE TABLE IF NOT EXISTS price_candles_1m (
    id             BIGSERIAL PRIMARY KEY,
    coin_id        TEXT NOT NULL,
    bucket         TIMESTAMPTZ NOT NULL,
    open           NUMERIC(24, 8) NOT NULL,
    high           NUMERIC(24, 8) NOT NULL,
    low            NUMERIC(24, 8) NOT NULL,
    close          NUMERIC(24, 8) NOT NULL,
    volume         NUMERIC(24, 8) NOT NULL DEFAULT 0,
    exchange_count SMALLINT NOT NULL DEFAULT 0,
    tick_count     INT NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS uidx_candles_1m_coin_bucket ON price_candles_1m (coin_id, bucket);
CREATE INDEX IF NOT EXISTS idx_candles_1m_bucket ON price_candles_1m (bucket DESC);

CREATE TABLE IF NOT EXISTS price_candles_5m (
    id             BIGSERIAL PRIMARY KEY,
    coin_id        TEXT NOT NULL,
    bucket         TIMESTAMPTZ NOT NULL,
    open           NUMERIC(24, 8) NOT NULL,
    high           NUMERIC(24, 8) NOT NULL,
    low            NUMERIC(24, 8) NOT NULL,
    close          NUMERIC(24, 8) NOT NULL,
    volume         NUMERIC(24, 8) NOT NULL DEFAULT 0,
    exchange_count SMALLINT NOT NULL DEFAULT 0,
    tick_count     INT NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS uidx_candles_5m_coin_bucket ON price_candles_5m (coin_id, bucket);
CREATE INDEX IF NOT EXISTS idx_candles_5m_bucket ON price_candles_5m (bucket DESC);

CREATE TABLE IF NOT EXISTS price_candles_1h (
    id             BIGSERIAL PRIMARY KEY,
    coin_id        TEXT NOT NULL,
    bucket         TIMESTAMPTZ NOT NULL,
    open           NUMERIC(24, 8) NOT NULL,
    high           NUMERIC(24, 8) NOT NULL,
    low            NUMERIC(24, 8) NOT NULL,
    close          NUMERIC(24, 8) NOT NULL,
    volume         NUMERIC(24, 8) NOT NULL DEFAULT 0,
    exchange_count SMALLINT NOT NULL DEFAULT 0,
    tick_count     INT NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS uidx_candles_1h_coin_bucket ON price_candles_1h (coin_id, bucket);
CREATE INDEX IF NOT EXISTS idx_candles_1h_bucket ON price_candles_1h (bucket DESC);

CREATE TABLE IF NOT EXISTS price_candles_1d (
    id             BIGSERIAL PRIMARY KEY,
    coin_id        TEXT NOT NULL,
    bucket         DATE NOT NULL,
    open           NUMERIC(24, 8) NOT NULL,
    high           NUMERIC(24, 8) NOT NULL,
    low            NUMERIC(24, 8) NOT NULL,
    close          NUMERIC(24, 8) NOT NULL,
    volume         NUMERIC(24, 8) NOT NULL DEFAULT 0,
    exchange_count SMALLINT NOT NULL DEFAULT 0,
    tick_count     INT NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS uidx_candles_1d_coin_bucket ON price_candles_1d (coin_id, bucket);
CREATE INDEX IF NOT EXISTS idx_candles_1d_bucket ON price_candles_1d (bucket DESC);

CREATE TABLE IF NOT EXISTS price_candles_1w (
    id             BIGSERIAL PRIMARY KEY,
    coin_id        TEXT NOT NULL,
    bucket         TIMESTAMPTZ NOT NULL,
    open           NUMERIC(24, 8) NOT NULL,
    high           NUMERIC(24, 8) NOT NULL,
    low            NUMERIC(24, 8) NOT NULL,
    close          NUMERIC(24, 8) NOT NULL,
    volume         NUMERIC(24, 8) NOT NULL DEFAULT 0,
    exchange_count SMALLINT NOT NULL DEFAULT 0,
    tick_count     INT NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS uidx_candles_1w_coin_bucket ON price_candles_1w (coin_id, bucket);
CREATE INDEX IF NOT EXISTS idx_candles_1w_bucket ON price_candles_1w (bucket DESC);

CREATE TABLE IF NOT EXISTS price_candles_1month (
    id             BIGSERIAL PRIMARY KEY,
    coin_id        TEXT NOT NULL,
    bucket         TIMESTAMPTZ NOT NULL,
    open           NUMERIC(24, 8) NOT NULL,
    high           NUMERIC(24, 8) NOT NULL,
    low            NUMERIC(24, 8) NOT NULL,
    close          NUMERIC(24, 8) NOT NULL,
    volume         NUMERIC(24, 8) NOT NULL DEFAULT 0,
    exchange_count SMALLINT NOT NULL DEFAULT 0,
    tick_count     INT NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS uidx_candles_1month_coin_bucket ON price_candles_1month (coin_id, bucket);
CREATE INDEX IF NOT EXISTS idx_candles_1month_bucket ON price_candles_1month (bucket DESC);

CREATE OR REPLACE VIEW candle_row_counts AS
SELECT 'price_candles_1m'     AS tbl, COUNT(*) AS rows FROM price_candles_1m
UNION ALL SELECT 'price_candles_5m',     COUNT(*) FROM price_candles_5m
UNION ALL SELECT 'price_candles_1h',     COUNT(*) FROM price_candles_1h
UNION ALL SELECT 'price_candles_1d',     COUNT(*) FROM price_candles_1d
UNION ALL SELECT 'price_candles_1w',     COUNT(*) FROM price_candles_1w
UNION ALL SELECT 'price_candles_1month', COUNT(*) FROM price_candles_1month;

-- ── 7. Admin table ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS admins (
  id         SERIAL PRIMARY KEY,
  username   TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── 8. (no seed data) ────────────────────────────────────────────────────────
-- Tables start empty. The score orchestrator populates coins and rating_scores
-- on its first run.
