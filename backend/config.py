"""
Application configuration.
Add new API provider configurations here.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file (ignored by git)
load_dotenv()

# CoinGecko API (free tier, primary provider)
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
COINGECKO_COINS_LIST_URL = "https://api.coingecko.com/api/v3/coins/list"

# Redis Cache Configuration
# Set via REDIS_URL in your .env file
# Note: Upstash Redis requires TLS (rediss:// protocol)
REDIS_URL = os.getenv("REDIS_URL")

# PostgreSQL Database Configuration (Supabase)
# Set via DATABASE_URL in your .env file
DATABASE_URL = os.getenv("DATABASE_URL")

# Cache TTL (time to live) in seconds
# Only tokenomics is cached (market cap, supply, etc. - frequently changing data)
# Static coin metadata (name, symbol, etc.) should be stored in SQL database
CACHE_TTL_TOKENOMICS = 600  # 10 minutes

# Real-time market data cache TTL (price, market cap, volume)
CACHE_TTL_REALTIME = 120  # 2 minutes

# Future API configurations (uncomment when implemented):
# COINMARKETCAP_API_KEY = "your_api_key_here"
# COINMARKETCAP_BASE_URL = "https://pro-api.coinmarketcap.com/v1"
# 
# CRYPTOCOMPARE_API_KEY = "your_api_key_here"
# CRYPTOCOMPARE_BASE_URL = "https://min-api.cryptocompare.com/data"
