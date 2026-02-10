CREATE TABLE coins (
  -- Core identifiers
  id TEXT PRIMARY KEY,                 -- "bitcoin", "ethereum"
  symbol TEXT NOT NULL,                -- "btc", "eth"
  name TEXT NOT NULL,                  -- "Bitcoin"

  -- Media / display
  image_url TEXT,

  -- Market cap metadata (semi-static)
  market_cap_rank INTEGER,
  circulating_supply NUMERIC,
  total_supply NUMERIC,
  max_supply NUMERIC,
  fully_diluted_valuation NUMERIC,

  -- All-time stats (rarely change)
  ath NUMERIC,
  ath_date TIMESTAMPTZ,
  atl NUMERIC,
  atl_date TIMESTAMPTZ,

  -- Your app-specific fields (optional, editable later)
  description TEXT,                    -- your own or cleaned CoinGecko text
  rating_score NUMERIC(4, 2),           -- e.g. 0–10 or 0–100
  rating_notes TEXT,                   -- internal notes
  review_count INTEGER,                -- optional aggregate
  is_featured BOOLEAN DEFAULT FALSE,

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_coins_market_cap_rank
ON coins (market_cap_rank);

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_coins_timestamp
BEFORE UPDATE ON coins
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();


