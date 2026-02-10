"""
Application configuration.
Add new API provider configurations here.
"""
import os

# CoinGecko API (free tier, primary provider)
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
COINGECKO_COINS_LIST_URL = "https://api.coingecko.com/api/v3/coins/list"

# Redis Cache Configuration
# Set via environment variable or use default
# Note: Upstash Redis requires TLS (rediss:// protocol)
REDIS_URL = os.getenv(
    "REDIS_URL",
    "rediss://default:AbM1AAIncDJmMDg0NGJiZTJhNTg0MmMzYjAyZmJjNjBlZDk1NWIwMXAyNDU4Nzc@natural-bluebird-45877.upstash.io:6379"
)

# Cache TTL (time to live) in seconds
# Only tokenomics is cached (market cap, supply, etc. - frequently changing data)
# Static coin metadata (name, symbol, etc.) should be stored in SQL database
CACHE_TTL_TOKENOMICS = 600  # 10 minutes

# Future API configurations (uncomment when implemented):
# COINMARKETCAP_API_KEY = "your_api_key_here"
# COINMARKETCAP_BASE_URL = "https://pro-api.coinmarketcap.com/v1"
# 
# CRYPTOCOMPARE_API_KEY = "your_api_key_here"
# CRYPTOCOMPARE_BASE_URL = "https://min-api.cryptocompare.com/data"
