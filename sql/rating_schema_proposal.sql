-- =============================================================================
-- Proposed Rating Schema
-- =============================================================================
-- This file defines the recommended schema for the rating engine and the
-- security/transparency tables. It is intended as a design proposal.
--
-- It preserves the existing `rating_scores` model while adding a clearer
-- separation between static coin metadata, analyst-owned security assumptions,
-- and dynamic decentralization/security snapshots.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Coin metadata and security profile
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS coins (
    id                 TEXT PRIMARY KEY,
    symbol             TEXT NOT NULL,
    name               TEXT NOT NULL,
    description        TEXT,
    image_url          TEXT,
    github_url         TEXT,
    max_supply         NUMERIC,

    -- Core security grouping
    consensus_type     TEXT NOT NULL
                           CHECK (consensus_type IN ('pow','pos','rollup','token','stable','hybrid')),
    network_layer      TEXT NOT NULL
                           CHECK (network_layer IN ('l1','l2','l3','sidechain','appchain','bridge')),
    token_category     TEXT NOT NULL
                           CHECK (token_category IN ('native','erc20','stablecoin','liquid_staking','governance','other')),

    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_coins_consensus_type ON coins(consensus_type);
CREATE INDEX IF NOT EXISTS idx_coins_network_layer ON coins(network_layer);
CREATE INDEX IF NOT EXISTS idx_coins_token_category ON coins(token_category);


-- -----------------------------------------------------------------------------
-- Static analyst / security assumptions
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS coin_security_profiles (
    coin_id                 TEXT PRIMARY KEY REFERENCES coins(id),
    security_model          TEXT,
    admin_control           TEXT,
    upgradeability_risk     TEXT,
    governance_notes        TEXT,
    team_allocation_pct     NUMERIC,
    treasury_allocation_pct NUMERIC,
    audit_status            TEXT,
    protocol_notes          TEXT,
    last_reviewed_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- -----------------------------------------------------------------------------
-- PoW native coin metadata
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pow_native_metadata (
    coin_id                 TEXT PRIMARY KEY REFERENCES coins(id),
    mining_algorithm        TEXT,
    pow_transparency_notes  TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pow_native_snapshots (
    id                     SERIAL PRIMARY KEY,
    coin_id                TEXT NOT NULL REFERENCES coins(id),
    snapshot_time          TIMESTAMPTZ NOT NULL,
    source                 TEXT NOT NULL,
    top_pool_pct           REAL,
    pool_count             INTEGER,
    nakamoto_coefficient   INTEGER,
    hashrate_hhi           REAL,
    top_holders_json       JSONB,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    refreshed_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pow_native_snapshots_coin_id ON pow_native_snapshots(coin_id);
CREATE INDEX IF NOT EXISTS idx_pow_native_snapshots_time ON pow_native_snapshots(snapshot_time DESC);


-- -----------------------------------------------------------------------------
-- PoS native coin metadata
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pos_native_metadata (
    coin_id                 TEXT PRIMARY KEY REFERENCES coins(id),
    unstake_period_days     INTEGER,
    pos_transparency_notes  TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pos_native_snapshots (
    id                       SERIAL PRIMARY KEY,
    coin_id                  TEXT NOT NULL REFERENCES coins(id),
    snapshot_time            TIMESTAMPTZ NOT NULL,
    source                   TEXT NOT NULL,
    validator_count          INTEGER,
    staked_pct               REAL,
    top_validator_pct        REAL,
    nakamoto_coefficient     INTEGER,
    delegation_concentration REAL,
    insider_pct              REAL,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    refreshed_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pos_native_snapshots_coin_id ON pos_native_snapshots(coin_id);
CREATE INDEX IF NOT EXISTS idx_pos_native_snapshots_time ON pos_native_snapshots(snapshot_time DESC);


-- -----------------------------------------------------------------------------
-- EVM Layer 2 / rollup metadata
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evm_layer2_metadata (
    coin_id                     TEXT PRIMARY KEY REFERENCES coins(id),
    l1_base                     TEXT,
    proof_type                  TEXT,
    operator_transparency       TEXT,
    challenge_window_hours      INTEGER,
    bridge_risk                 TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evm_layer2_snapshots (
    id                           SERIAL PRIMARY KEY,
    coin_id                      TEXT NOT NULL REFERENCES coins(id),
    snapshot_time                TIMESTAMPTZ NOT NULL,
    source                       TEXT NOT NULL,
    sequencer_centralization_pct REAL,
    bridge_risk_score            REAL,
    created_at                   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    refreshed_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evm_layer2_snapshots_coin_id ON evm_layer2_snapshots(coin_id);
CREATE INDEX IF NOT EXISTS idx_evm_layer2_snapshots_time ON evm_layer2_snapshots(snapshot_time DESC);


-- -----------------------------------------------------------------------------
-- Stablecoin metadata
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stablecoin_metadata (
    coin_id                    TEXT PRIMARY KEY REFERENCES coins(id),
    reserve_type               TEXT,
    audit_frequency            TEXT,
    peg_mechanism              TEXT,
    redemption_mechanism       TEXT,
    issuer_regulatory_status   TEXT,
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS stablecoin_snapshots (
    id                           SERIAL PRIMARY KEY,
    coin_id                      TEXT NOT NULL REFERENCES coins(id),
    snapshot_time                TIMESTAMPTZ NOT NULL,
    source                       TEXT NOT NULL,
    reserve_transparency_score   REAL,
    reserve_composition_json     JSONB,
    created_at                   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    refreshed_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stablecoin_snapshots_coin_id ON stablecoin_snapshots(coin_id);
CREATE INDEX IF NOT EXISTS idx_stablecoin_snapshots_time ON stablecoin_snapshots(snapshot_time DESC);


-- -----------------------------------------------------------------------------
-- Token metadata
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS token_metadata (
    coin_id                 TEXT PRIMARY KEY REFERENCES coins(id),
    contract_admin_status   TEXT,
    audit_status            TEXT,
    token_transparency_notes TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS token_snapshots (
    id                       SERIAL PRIMARY KEY,
    coin_id                  TEXT NOT NULL REFERENCES coins(id),
    snapshot_time            TIMESTAMPTZ NOT NULL,
    source                   TEXT NOT NULL,
    holder_count             INTEGER,
    top_1_pct                REAL,
    top_10_pct               REAL,
    treasury_pct             REAL,
    vesting_pct              REAL,
    top_holders_json         JSONB,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    refreshed_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_token_snapshots_coin_id ON token_snapshots(coin_id);
CREATE INDEX IF NOT EXISTS idx_token_snapshots_time ON token_snapshots(snapshot_time DESC);


-- -----------------------------------------------------------------------------
-- Rating output tables
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rating_scores (
    coin_id                TEXT PRIMARY KEY REFERENCES coins(id),
    coin_symbol            TEXT NOT NULL,
    overall_score          NUMERIC(5,2) NOT NULL CHECK (overall_score BETWEEN 0 AND 100),
    automated_score        NUMERIC(5,2) NOT NULL CHECK (automated_score BETWEEN 0 AND 75),
    manual_validation      NUMERIC(5,2) NOT NULL DEFAULT 25 CHECK (manual_validation BETWEEN 0 AND 25),
    risk_level             TEXT CHECK (risk_level IN ('Low','Moderate','High')),
    review_status          TEXT NOT NULL DEFAULT 'pending'
                               CHECK (review_status IN ('pending','complete','archived')),
    security_transparency  JSONB NOT NULL DEFAULT '{}',
    tokenomics_utility     JSONB NOT NULL DEFAULT '{}',
    community_dev_activity JSONB NOT NULL DEFAULT '{}',
    public_discourse       JSONB NOT NULL DEFAULT '{}',
    score_history          JSONB NOT NULL DEFAULT '[]',
    score_history_count    INTEGER NOT NULL DEFAULT 0,
    last_computed_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rating_scores_overall ON rating_scores(overall_score DESC);
CREATE INDEX IF NOT EXISTS idx_rating_scores_risk    ON rating_scores(risk_level);
CREATE INDEX IF NOT EXISTS idx_rating_scores_status  ON rating_scores(review_status);


-- -----------------------------------------------------------------------------
-- Rating score history tracking
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION rating_scores_append_history()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.overall_score IS DISTINCT FROM OLD.overall_score THEN
        NEW.score_history = COALESCE(OLD.score_history, '[]'::jsonb)
            || jsonb_build_array(OLD.overall_score);
        NEW.score_history_count = COALESCE(OLD.score_history_count, 0) + 1;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_rating_scores_append_history
BEFORE UPDATE ON rating_scores
FOR EACH ROW
WHEN (OLD.overall_score IS DISTINCT FROM NEW.overall_score)
EXECUTE FUNCTION rating_scores_append_history();
