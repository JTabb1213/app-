"""
Market collector — config
"""
import os

DATABASE_URL              = os.getenv("DATABASE_URL", "postgresql://dev:devpassword@postgres:5432/cryptorating")
REDIS_URL                 = os.getenv("REDIS_URL",    "redis://redis:6379")
COINGECKO_KEY             = os.getenv("COINGECKO_API_KEY", "")

# Base URL for the CoinGecko REST API (v3). Override to point at a proxy or demo endpoint.
COINGECKO_API_BASE_URL    = os.getenv("COINGECKO_API_BASE_URL", "https://api.coingecko.com/api/v3")

# How long market data stays fresh in Redis (seconds)
REDIS_TTL       = int(os.getenv("MARKET_REDIS_TTL", str(6 * 3600)))   # 6 h

# How often the collector runs a full refresh cycle (seconds)
RUN_INTERVAL    = int(os.getenv("MARKET_RUN_INTERVAL", str(6 * 3600))) # 6 h

# Pause between individual CoinGecko coin requests to avoid rate limits
REQUEST_DELAY   = float(os.getenv("MARKET_REQUEST_DELAY", "1.5"))      # seconds

# Batch size for CoinGecko /coins/markets endpoint (max 250)
BATCH_SIZE      = int(os.getenv("MARKET_BATCH_SIZE", "50"))

LOG_LEVEL       = os.getenv("LOG_LEVEL", "INFO")
