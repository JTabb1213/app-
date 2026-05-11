CREATE TABLE coins (
  -- Core identifiers
  id TEXT PRIMARY KEY,                 -- "bitcoin", "ethereum"
  symbol TEXT NOT NULL,                -- "btc", "eth"
  name TEXT NOT NULL,                  -- "Bitcoin"

  -- Media / links
  image_url TEXT,
  github_url TEXT,

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

  -- App-specific fields
  description TEXT,
  rating_score NUMERIC(4, 2),
  rating_notes TEXT,
  review_count INTEGER,
  is_featured BOOLEAN DEFAULT FALSE,

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_coins_market_cap_rank ON public.coins(market_cap_rank);
CREATE INDEX idx_coins_symbol ON public.coins(symbol);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_set_updated_at ON public.coins;

CREATE TRIGGER trg_set_updated_at
BEFORE UPDATE ON public.coins
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
