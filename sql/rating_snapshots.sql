-- =============================================================================
-- rating_scores — current composite score and category breakdown
-- =============================================================================
-- Stores the current CCS (Comprehensive Coin Score) and its five category scores.
-- One row per coin with the latest snapshot.
--
-- Categories (with max points):
--   - Security & Transparency (35 pts)
--   - Tokenomics & Utility (20 pts)
--   - Community & Dev Activity (15 pts)
--   - Public Discourse Signal (5 pts)
--
-- Scoring breakdown:
--   overall_score = automated_score + manual_validation
--   automated_score = sum of all category scores (calculated)
--   manual_validation = analyst review (default 25, max 25)
--
-- Category structure (JSONB): { score, max, metrics: { ... } }
-- =============================================================================

CREATE TABLE IF NOT EXISTS rating_scores (
    id                          BIGSERIAL PRIMARY KEY,
    
    -- Identity --
    coin_id                     TEXT NOT NULL UNIQUE,  -- CoinGecko canonical id (e.g. "bitcoin")
    coin_symbol                 TEXT NOT NULL,         -- e.g. "BTC"
    
    -- Overall Scores --
    overall_score               DECIMAL(5, 2) NOT NULL CHECK (overall_score >= 0 AND overall_score <= 100),
    automated_score             DECIMAL(5, 2) NOT NULL CHECK (automated_score >= 0 AND automated_score <= 75),
    manual_validation           DECIMAL(5, 2) NOT NULL DEFAULT 25 CHECK (manual_validation >= 0 AND manual_validation <= 25),
    
    -- Risk Assessment --
    risk_level                  VARCHAR(20),           -- 'Low' | 'Moderate' | 'High' (derived from overall_score)
    
    -- Category Scores (JSONB structure: {score, max, metrics: {...}}) --
    security_transparency       JSONB NOT NULL DEFAULT '{}',       -- score/35, includes holder diversity, top 10 concentration, largest wallet %
    tokenomics_utility          JSONB NOT NULL DEFAULT '{}',       -- score/20, includes max supply (capped/uncapped), inflation potential
    community_dev_activity      JSONB NOT NULL DEFAULT '{}',       -- score/15, includes delta_commits (since last run), contributor count
    public_discourse            JSONB NOT NULL DEFAULT '{}',       -- score/5, includes social sentiment, search interest
    
    -- Metadata --
    last_computed_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    review_status               VARCHAR(20) NOT NULL DEFAULT 'pending', -- 'pending' | 'complete' | 'archived'
    
    -- Audit Timestamps --
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS rating_scores_coin_id_idx ON rating_scores (coin_id);
CREATE INDEX IF NOT EXISTS rating_scores_overall_score_idx ON rating_scores (overall_score DESC);
CREATE INDEX IF NOT EXISTS rating_scores_review_status_idx ON rating_scores (review_status);
CREATE INDEX IF NOT EXISTS rating_scores_risk_level_idx ON rating_scores (risk_level);

-- Auto-update timestamp and trigger history archival
CREATE OR REPLACE FUNCTION update_rating_scores_timestamp()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ IMMUTABLE;

DROP TRIGGER IF EXISTS rating_scores_update_timestamp ON rating_scores;
CREATE TRIGGER rating_scores_update_timestamp
BEFORE UPDATE ON rating_scores
FOR EACH ROW
EXECUTE FUNCTION update_rating_scores_timestamp();


-- =============================================================================
-- rating_score_history — immutable archive of score snapshots
-- =============================================================================
-- Stores complete historical snapshots of scores for trend analysis.
-- Automatically populated by trigger when rating_scores is updated.
--
-- snapshots JSONB ARRAY contains historical records:
-- [
--   {
--     "timestamp": "2026-05-09T14:30:00Z",
--     "overall_score": 82.5,
--     "automated_score": 57.5,
--     "manual_validation": 25,
--     "risk_level": "Low",
--     "security_transparency": {...},
--     "tokenomics_utility": {...},
--     ...
--   },
--   ...
-- ]
-- =============================================================================

CREATE TABLE IF NOT EXISTS rating_score_history (
    id                  BIGSERIAL PRIMARY KEY,
    
    -- Identity --
    coin_id             TEXT NOT NULL,  -- CoinGecko canonical id (references rating_scores)
    
    -- Historical Snapshots (ordered array) --
    snapshots           JSONB NOT NULL DEFAULT '[]',  -- Array of historical score objects
    
    -- Metadata --
    snapshot_count      INTEGER NOT NULL DEFAULT 0,   -- Number of snapshots in array
    first_snapshot_at   TIMESTAMPTZ,
    last_snapshot_at    TIMESTAMPTZ,
    
    -- Audit --
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT rating_score_history_coin_id_unique UNIQUE (coin_id)
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS rating_score_history_coin_id_idx ON rating_score_history (coin_id);

-- Function to append new snapshot to history when rating_scores is updated
CREATE OR REPLACE FUNCTION append_score_to_history()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    new_snapshot JSONB;
BEGIN
    -- Build snapshot object from the OLD record (before update)
    new_snapshot := jsonb_build_object(
        'timestamp', NOW()::TEXT,
        'overall_score', OLD.overall_score,
        'automated_score', OLD.automated_score,
        'manual_validation', OLD.manual_validation,
        'risk_level', OLD.risk_level,
        'security_transparency', OLD.security_transparency,
        'tokenomics_utility', OLD.tokenomics_utility,
        'community_dev_activity', OLD.community_dev_activity,
        'public_discourse', OLD.public_discourse
    );
    
    -- Insert or update history record
    INSERT INTO rating_score_history (coin_id, snapshots, snapshot_count, first_snapshot_at, last_snapshot_at, updated_at)
    VALUES (
        NEW.coin_id,
        ARRAY[new_snapshot]::JSONB[],
        1,
        NOW(),
        NOW(),
        NOW()
    )
    ON CONFLICT (coin_id) DO UPDATE SET
        snapshots = array_append(rating_score_history.snapshots, new_snapshot),
        snapshot_count = rating_score_history.snapshot_count + 1,
        last_snapshot_at = NOW(),
        updated_at = NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-archive before update
DROP TRIGGER IF EXISTS archive_score_to_history ON rating_scores;
CREATE TRIGGER archive_score_to_history
BEFORE UPDATE ON rating_scores
FOR EACH ROW
WHEN (OLD.overall_score IS DISTINCT FROM NEW.overall_score OR 
      OLD.automated_score IS DISTINCT FROM NEW.automated_score OR
      OLD.manual_validation IS DISTINCT FROM NEW.manual_validation)
EXECUTE FUNCTION append_score_to_history();


-- Auto-update history timestamp
DROP TRIGGER IF EXISTS rating_score_history_update_timestamp ON rating_score_history;
CREATE TRIGGER rating_score_history_update_timestamp
BEFORE UPDATE ON rating_score_history
FOR EACH ROW
EXECUTE FUNCTION update_rating_scores_timestamp();


-- =============================================================================
-- SAMPLE DATA / DOCUMENTATION
-- =============================================================================
-- Example of inserting a score with category breakdown:
--
-- INSERT INTO rating_scores (
--   coin_id, coin_symbol, overall_score, automated_score, manual_validation, risk_level,
--   security_transparency, tokenomics_utility, community_dev_activity, public_discourse
-- ) VALUES (
--   'bitcoin', 'BTC', 82.5, 57.5, 25, 'Low',
--   '{"score": 30, "max": 35, "metrics": {"top_10_pct": 15, "largest_wallet_pct": 10, "holder_count": 5}}'::jsonb,
--   '{"score": 18, "max": 20, "metrics": {"has_max_supply": 10, "inflation_potential": 8}}'::jsonb,
--   '{"score": 13, "max": 15, "metrics": {"delta_commits": 7, "contributor_count": 6}}'::jsonb,
--   '{"score": 4, "max": 5, "metrics": {"social_sentiment": 2, "search_interest": 2}}'::jsonb
-- );
--
-- overall_score = automated_score + manual_validation
-- manual_validation is set by analysts (default 25, max 25)
-- History automatically populated on first UPDATE to rating_scores for that coin.
