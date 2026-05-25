-- Separate table for coin network/scalability metrics.
-- This keeps chain-specific network metrics out of the main coins table.

CREATE TABLE IF NOT EXISTS coin_network_metrics (
  id SERIAL PRIMARY KEY,
  coin_id TEXT NOT NULL REFERENCES coins(id) ON DELETE CASCADE,
  metric_name TEXT NOT NULL,
  metric_value NUMERIC,
  metric_text TEXT,
  source TEXT,
  as_of_date DATE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_coin_network_metrics_coin_id ON coin_network_metrics(coin_id);
CREATE INDEX IF NOT EXISTS idx_coin_network_metrics_name ON coin_network_metrics(metric_name);

CREATE OR REPLACE FUNCTION set_updated_at_coin_network_metrics()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_set_updated_at_coin_network_metrics ON coin_network_metrics;

CREATE TRIGGER trg_set_updated_at_coin_network_metrics
BEFORE UPDATE ON coin_network_metrics
FOR EACH ROW
EXECUTE FUNCTION set_updated_at_coin_network_metrics();
