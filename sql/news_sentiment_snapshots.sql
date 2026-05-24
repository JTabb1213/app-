-- News sentiment snapshots
-- One row per coin per 4-hour bucket.
-- Written by the news-sentiment-collector service.
-- Read by the rating score-orchestrator (public discourse scorer).

CREATE TABLE IF NOT EXISTS news_sentiment_snapshots (
    coin_id       TEXT        NOT NULL,
    bucket_start  TIMESTAMPTZ NOT NULL,
    avg_score     FLOAT,                     -- VADER compound average (-1 to 1)
    article_count INT         NOT NULL DEFAULT 0,
    articles      JSONB,                     -- { "url": score, ... }
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (coin_id, bucket_start)
);

CREATE INDEX IF NOT EXISTS idx_nss_coin_bucket
    ON news_sentiment_snapshots (coin_id, bucket_start DESC);
