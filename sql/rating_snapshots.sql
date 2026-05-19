-- =============================================================================
-- rating_scores + rating_score_history
-- =============================================================================

CREATE TABLE IF NOT EXISTS rating_scores (
    coin_id                TEXT         PRIMARY KEY,
    coin_symbol            TEXT         NOT NULL,
    overall_score          NUMERIC(5,2) NOT NULL CHECK (overall_score   BETWEEN 0 AND 100),
    automated_score        NUMERIC(5,2) NOT NULL CHECK (automated_score BETWEEN 0 AND 75),
    manual_validation      NUMERIC(5,2) NOT NULL DEFAULT 25 CHECK (manual_validation BETWEEN 0 AND 25),
    risk_level             TEXT         CHECK (risk_level IN ('Low','Moderate','High')),
    review_status          TEXT         NOT NULL DEFAULT 'pending' CHECK (review_status IN ('pending','complete','archived')),
    security_transparency  JSONB        NOT NULL DEFAULT '{}',
    tokenomics_utility     JSONB        NOT NULL DEFAULT '{}',
    community_dev_activity JSONB        NOT NULL DEFAULT '{}',
    public_discourse       JSONB        NOT NULL DEFAULT '{}',
    -- Compact score history: [{score: 81.0, date: "2026-05-18"}, ...]
    -- Appended automatically by trigger whenever overall_score changes.
    -- Use for the CCS Score Trend chart.
    score_history          JSONB        NOT NULL DEFAULT '[]',
    last_computed_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rating_overall ON rating_scores (overall_score DESC);
CREATE INDEX IF NOT EXISTS idx_rating_risk    ON rating_scores (risk_level);
CREATE INDEX IF NOT EXISTS idx_rating_status  ON rating_scores (review_status);

-- Append old score to score_history array when overall_score changes.
-- Keeps only the last 52 entries (one year of weekly runs).
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

DROP TRIGGER IF EXISTS trg_rating_updated_at  ON rating_scores;
DROP TRIGGER IF EXISTS trg_archive_rating     ON rating_scores;
DROP TRIGGER IF EXISTS trg_score_history      ON rating_scores;
CREATE TRIGGER trg_score_history
BEFORE UPDATE ON rating_scores
FOR EACH ROW EXECUTE FUNCTION fn_append_score_history();


-- =============================================================================
-- Example UPSERT (score-orchestrator writes this after every scoring run)
-- =============================================================================
-- INSERT INTO rating_scores (
--   coin_id, coin_symbol, overall_score, automated_score, manual_validation,
--   risk_level, security_transparency, tokenomics_utility,
--   community_dev_activity, public_discourse
-- ) VALUES (
--   'bitcoin', 'BTC', 82.5, 57.5, 25, 'Low',
--   '{"score":30,"max":35,"metrics":{"top_10_pct":15,"largest_wallet_pct":10}}',
--   '{"score":18,"max":20,"metrics":{"has_max_supply":10,"inflation_potential":8}}',
--   '{"score":13,"max":15,"metrics":{"delta_commits":7,"contributor_count":6}}',
--   '{"score":4,"max":5,"metrics":{"social_sentiment":2,"search_interest":2}}'
-- )
-- ON CONFLICT (coin_id) DO UPDATE SET
--   coin_symbol=EXCLUDED.coin_symbol, overall_score=EXCLUDED.overall_score,
--   automated_score=EXCLUDED.automated_score, manual_validation=EXCLUDED.manual_validation,
--   risk_level=EXCLUDED.risk_level, review_status=EXCLUDED.review_status,
--   security_transparency=EXCLUDED.security_transparency,
--   tokenomics_utility=EXCLUDED.tokenomics_utility,
--   community_dev_activity=EXCLUDED.community_dev_activity,
--   public_discourse=EXCLUDED.public_discourse,
--   last_computed_at=NOW();
-- (trigger fires automatically and archives old row to rating_score_history on score change)
