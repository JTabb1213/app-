-- ─────────────────────────────────────────────────────────────────────────────
-- Decentralization Risk Snapshots
-- Replaces the old holder_snapshots / holder_snapshots_history tables.
--
-- Supports four diversity_method values:
--   token_holders  — ERC-20 richlist (Covalent)
--   hashrate       — BTC miner pool concentration (mempool.space)
--   validator      — ETH staking entity concentration (rated.network)
--   vesting        — PoS L1 insider / team / VC allocation
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE decentralization_snapshots (
  -- Primary key
  id SERIAL PRIMARY KEY,

  -- Coin / Token identifiers
  coin_id            TEXT NOT NULL,              -- "chainlink", "bitcoin", "solana", etc.
  diversity_method   TEXT NOT NULL DEFAULT 'token_holders',
                                                 -- "token_holders"|"hashrate"|"validator"|"vesting"
  chain              TEXT,                       -- "eth-mainnet", "matic-mainnet", etc. (token_holders only)
  contract_address   TEXT,                       -- EVM: 0x... (token_holders only)

  -- Snapshot metadata
  snapshot_time TIMESTAMPTZ NOT NULL,            -- When the snapshot was taken
  source TEXT NOT NULL,                          -- "covalent", "mempool.space", "rated.network", "CoinGecko"

  -- ── Richlist concentration (token_holders) ──────────────────────────────
  holder_count INTEGER,                          -- Total unique holder addresses
  top_1_pct    REAL,                             -- % held by top 1 holder/pool/entity
  top_10_pct   REAL,                             -- % held by top 10 holders/pools/entities
  top_100_pct  REAL,                             -- % held by top 100 (richlist only)

  -- Advanced concentration metrics (token_holders + hashrate + validator)
  gini_coefficient REAL,                         -- 0 = equal, 1 = one holder
  hhi              REAL,                         -- Herfindahl-Hirschman Index

  -- ── Consensus power concentration (hashrate + validator) ────────────────
  nakamoto_coefficient INTEGER,                  -- Min entities to control 51% (BTC) or 33% (ETH)

  -- ── Insider / vesting risk (vesting) ────────────────────────────────────
  insider_pct        REAL,                       -- % of supply held by team/VCs/foundation
  circulating_ratio  REAL,                       -- circulating / total supply (0-1)
  risk_flags         TEXT[],                     -- Notable risk flags from research

  -- Top 10 entities snapshot (all methods)
  top_holders_json JSONB,                        -- [{rank, address/name, pct}, ...]

  -- Timestamps
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  refreshed_at TIMESTAMPTZ DEFAULT NOW(),

  -- One latest snapshot per coin (latest overwrites, history in _history table)
  CONSTRAINT unique_coin_latest UNIQUE (coin_id)
);

-- Indexes
CREATE INDEX idx_decentral_coin_id      ON decentralization_snapshots(coin_id);
CREATE INDEX idx_decentral_method       ON decentralization_snapshots(diversity_method);
CREATE INDEX idx_decentral_snapshot_time ON decentralization_snapshots(snapshot_time DESC);
CREATE INDEX idx_decentral_created_at   ON decentralization_snapshots(created_at DESC);


-- ─────────────────────────────────────────────────────────────────────────────
-- Historical snapshots — versioned archive for trend analysis
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE decentralization_snapshots_history (
  id SERIAL PRIMARY KEY,
  coin_id            TEXT NOT NULL,
  diversity_method   TEXT NOT NULL DEFAULT 'token_holders',
  chain              TEXT,
  contract_address   TEXT,
  snapshot_time      TIMESTAMPTZ NOT NULL,
  source             TEXT NOT NULL,
  holder_count       INTEGER,
  top_1_pct          REAL,
  top_10_pct         REAL,
  top_100_pct        REAL,
  gini_coefficient   REAL,
  hhi                REAL,
  nakamoto_coefficient INTEGER,
  insider_pct        REAL,
  circulating_ratio  REAL,
  risk_flags         TEXT[],
  top_holders_json   JSONB,
  created_at         TIMESTAMPTZ DEFAULT NOW(),
  refreshed_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_decentral_hist_coin_time ON decentralization_snapshots_history(coin_id, snapshot_time DESC);
CREATE INDEX idx_decentral_hist_time      ON decentralization_snapshots_history(snapshot_time DESC);
CREATE INDEX idx_decentral_hist_method    ON decentralization_snapshots_history(diversity_method);


-- ─────────────────────────────────────────────────────────────────────────────
-- Trigger: Archive current snapshot before each update
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION archive_decentralization_snapshot()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'UPDATE' THEN
    INSERT INTO decentralization_snapshots_history (
      coin_id, diversity_method, chain, contract_address,
      snapshot_time, source,
      holder_count, top_1_pct, top_10_pct, top_100_pct,
      gini_coefficient, hhi,
      nakamoto_coefficient,
      insider_pct, circulating_ratio, risk_flags,
      top_holders_json,
      created_at, refreshed_at
    ) VALUES (
      OLD.coin_id, OLD.diversity_method, OLD.chain, OLD.contract_address,
      OLD.snapshot_time, OLD.source,
      OLD.holder_count, OLD.top_1_pct, OLD.top_10_pct, OLD.top_100_pct,
      OLD.gini_coefficient, OLD.hhi,
      OLD.nakamoto_coefficient,
      OLD.insider_pct, OLD.circulating_ratio, OLD.risk_flags,
      OLD.top_holders_json,
      OLD.created_at, OLD.refreshed_at
    );
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_archive_decentralization_snapshot ON decentralization_snapshots;

CREATE TRIGGER trg_archive_decentralization_snapshot
BEFORE UPDATE ON decentralization_snapshots
FOR EACH ROW
EXECUTE FUNCTION archive_decentralization_snapshot();


-- ─────────────────────────────────────────────────────────────────────────────
-- View: Latest snapshot per coin with method label
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW v_latest_decentralization AS
SELECT
  coin_id,
  diversity_method,
  snapshot_time,
  source,
  -- Universal fields
  top_1_pct,
  top_10_pct,
  gini_coefficient,
  hhi,
  -- Method-specific
  holder_count,
  nakamoto_coefficient,
  insider_pct,
  circulating_ratio,
  top_holders_json
FROM decentralization_snapshots;


-- ─────────────────────────────────────────────────────────────────────────────
-- View: 30-day Nakamoto coefficient trend (hashrate + validator)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW v_nakamoto_trend_30d AS
WITH ranked AS (
  SELECT
    coin_id,
    diversity_method,
    snapshot_time,
    nakamoto_coefficient,
    LAG(nakamoto_coefficient) OVER (PARTITION BY coin_id ORDER BY snapshot_time) AS prev_nakamoto
  FROM decentralization_snapshots_history
  WHERE snapshot_time > NOW() - INTERVAL '30 days'
    AND diversity_method IN ('hashrate', 'validator')
)
SELECT
  coin_id,
  diversity_method,
  snapshot_time,
  nakamoto_coefficient,
  (nakamoto_coefficient - prev_nakamoto) AS nakamoto_change,
  CASE
    WHEN prev_nakamoto IS NULL                              THEN 'first_snapshot'
    WHEN nakamoto_coefficient > prev_nakamoto               THEN 'improving'
    WHEN nakamoto_coefficient < prev_nakamoto               THEN 'worsening'
    ELSE                                                         'stable'
  END AS trend
FROM ranked;


-- ─────────────────────────────────────────────────────────────────────────────
-- Migrate existing data from old holder_snapshots (run once, then drop old tables)
-- ─────────────────────────────────────────────────────────────────────────────
-- INSERT INTO decentralization_snapshots (
--   coin_id, diversity_method, chain, contract_address,
--   snapshot_time, source,
--   holder_count, top_1_pct, top_10_pct, top_100_pct,
--   gini_coefficient, hhi,
--   created_at, refreshed_at
-- )
-- SELECT
--   coin_id, 'token_holders', chain, contract_address,
--   snapshot_time, source,
--   holder_count, top_1_pct, top_10_pct, top_100_pct,
--   gini_coefficient, hhi,
--   created_at, refreshed_at
-- FROM holder_snapshots
-- ON CONFLICT (coin_id) DO NOTHING;
--
-- DROP TABLE IF EXISTS holder_snapshots CASCADE;
-- DROP TABLE IF EXISTS holder_snapshots_history CASCADE;
