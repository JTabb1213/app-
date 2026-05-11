-- ─────────────────────────────────────────────────────────────────────────────
-- Holder Diversity Snapshots
-- Stores on-chain holder distribution metrics for tokens across all chains
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE holder_snapshots (
  -- Primary key
  id SERIAL PRIMARY KEY,

  -- Coin / Token identifiers
  coin_id TEXT NOT NULL,                 -- "chainlink", "uniswap", etc.
  chain TEXT NOT NULL,                   -- "ethereum", "polygon", "solana", "cardano"
  contract_address TEXT,                 -- EVM: 0x..., Cardano: policy_id+asset_name, Solana: mint pubkey

  -- Snapshot metadata
  snapshot_time TIMESTAMPTZ NOT NULL,    -- When the snapshot was taken
  source TEXT NOT NULL,                  -- "Etherscan", "Polygonscan", "Blockfrost", "Koios", "Solscan", "The Graph"

  -- Supply information
  total_supply NUMERIC NOT NULL,         -- Raw token units (not normalized)
  decimals INTEGER,                      -- Token decimal places (for normalization)

  -- Holder distribution metrics
  holder_count INTEGER,                  -- Total number of unique holder addresses
  top_1_pct REAL,                        -- Percentage held by top 1 holder
  top_10_pct REAL,                       -- Percentage held by top 10 holders
  top_100_pct REAL,                      -- Percentage held by top 100 holders
  
  -- Advanced concentration metrics
  gini_coefficient REAL,                 -- Gini coefficient (0 = equal distribution, 1 = one holder)
  hhi REAL,                              -- Herfindahl-Hirschman Index (concentration measure)

  -- Raw data storage (optional, for audits)
  raw_snapshot_path TEXT,                -- S3 path or local path to full holder JSON
  raw_snapshot_json JSONB,               -- Optionally store JSON inline (limit to top 1000)

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  refreshed_at TIMESTAMPTZ DEFAULT NOW(),

  -- Unique constraint (one latest snapshot per coin per chain)
  CONSTRAINT unique_coin_chain_latest UNIQUE (coin_id, chain)
);

-- Indexes for common queries
CREATE INDEX idx_holder_snapshots_coin_id ON holder_snapshots(coin_id);
CREATE INDEX idx_holder_snapshots_chain ON holder_snapshots(chain);
CREATE INDEX idx_holder_snapshots_snapshot_time ON holder_snapshots(snapshot_time DESC);
CREATE INDEX idx_holder_snapshots_coin_chain_time ON holder_snapshots(coin_id, chain, snapshot_time DESC);
CREATE INDEX idx_holder_snapshots_created_at ON holder_snapshots(created_at DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- Historical snapshots
-- Keeps a versioned history of all snapshots for trend analysis
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE holder_snapshots_history (
  -- Identical schema to holder_snapshots, but we allow duplicates
  id SERIAL PRIMARY KEY,
  coin_id TEXT NOT NULL,
  chain TEXT NOT NULL,
  contract_address TEXT,
  snapshot_time TIMESTAMPTZ NOT NULL,
  source TEXT NOT NULL,
  total_supply NUMERIC NOT NULL,
  decimals INTEGER,
  holder_count INTEGER,
  top_1_pct REAL,
  top_10_pct REAL,
  top_100_pct REAL,
  gini_coefficient REAL,
  hhi REAL,
  raw_snapshot_path TEXT,
  raw_snapshot_json JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  refreshed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for historical queries
CREATE INDEX idx_holder_history_coin_chain_time ON holder_snapshots_history(coin_id, chain, snapshot_time DESC);
CREATE INDEX idx_holder_history_snapshot_time ON holder_snapshots_history(snapshot_time DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- Trigger: Copy snapshots to history before updating
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION archive_holder_snapshot()
RETURNS TRIGGER AS $$
BEGIN
  -- If updating an existing snapshot, archive the old one first
  IF TG_OP = 'UPDATE' THEN
    INSERT INTO holder_snapshots_history
    SELECT * FROM (SELECT OLD.*) AS old_row;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_archive_holder_snapshot ON holder_snapshots;

CREATE TRIGGER trg_archive_holder_snapshot
BEFORE UPDATE ON holder_snapshots
FOR EACH ROW
EXECUTE FUNCTION archive_holder_snapshot();

-- ─────────────────────────────────────────────────────────────────────────────
-- View: Latest snapshots for all coins
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW v_latest_holder_snapshots AS
SELECT DISTINCT ON (coin_id, chain)
  coin_id,
  chain,
  contract_address,
  snapshot_time,
  source,
  total_supply,
  decimals,
  holder_count,
  top_1_pct,
  top_10_pct,
  top_100_pct,
  gini_coefficient,
  hhi,
  created_at,
  refreshed_at
FROM holder_snapshots_history
ORDER BY coin_id, chain, snapshot_time DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- View: 7-day trend (concentration change)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW v_holder_trend_7d AS
WITH ranked AS (
  SELECT
    coin_id,
    chain,
    snapshot_time,
    top_10_pct,
    LAG(top_10_pct) OVER (PARTITION BY coin_id, chain ORDER BY snapshot_time) AS prev_top_10_pct,
    ROW_NUMBER() OVER (PARTITION BY coin_id, chain ORDER BY snapshot_time DESC) AS rn
  FROM holder_snapshots_history
  WHERE snapshot_time > NOW() - INTERVAL '7 days'
)
SELECT
  coin_id,
  chain,
  snapshot_time,
  top_10_pct,
  (top_10_pct - prev_top_10_pct) AS change_pct,
  CASE
    WHEN prev_top_10_pct IS NULL THEN 'first_snapshot'
    WHEN top_10_pct > prev_top_10_pct THEN 'concentrating'
    WHEN top_10_pct < prev_top_10_pct THEN 'dispersing'
    ELSE 'stable'
  END AS trend
FROM ranked
WHERE rn <= 2;  -- Latest 2 snapshots per coin/chain

-- ─────────────────────────────────────────────────────────────────────────────
-- Maintenance: Retention policy
-- Keep full snapshots for 90 days, weekly summaries beyond that
-- ─────────────────────────────────────────────────────────────────────────────

-- Run this periodically to archive old snapshots:
-- DELETE FROM holder_snapshots_history
-- WHERE snapshot_time < NOW() - INTERVAL '180 days'
-- AND DATE_PART('dow', snapshot_time) != 1;  -- Keep Mondays only for retention

