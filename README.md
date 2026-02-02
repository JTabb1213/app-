# Adding New API Providers

This guide explains how to add new cryptocurrency data providers (like CoinMarketCap, CryptoCompare, etc.) with automatic fallback support.

## Quick Start

Your app now uses a **unified data service** that automatically tries multiple APIs if one fails or gets rate-limited.

## Current Structure

```
backend/services/
├── apis/
│   ├── base_provider.py      # Abstract base class
│   ├── coingecko.py          # CoinGecko implementation (active)
│   └── github.py             # GitHub metrics (separate)
├── data_service.py           # Unified service with fallback
├── scoring_service.py        # Uses data_service
└── tokenomics_service.py     # Uses data_service
```

## How to Add a New Provider

### Step 1: Create Provider Class

Create a new file in `services/apis/` (e.g., `coinmarketcap.py`):

```python
import requests
from .base_provider import CryptoDataProvider

class CoinMarketCapProvider(CryptoDataProvider):
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://pro-api.coinmarketcap.com/v1"
    
    def get_provider_name(self) -> str:
        return "CoinMarketCap"
    
    def check_health(self) -> bool:
        # Check if API is accessible
        try:
            response = requests.get(
                f"{self.base_url}/cryptocurrency/map",
                headers={"X-CMC_PRO_API_KEY": self.api_key},
                timeout=3
            )
            return response.status_code == 200
        except:
            return False
    
    def resolve_coin_id(self, query: str) -> str:
        # Implement coin search/resolution logic
        # Return CMC-specific coin ID
        pass
    
    def get_coin_data(self, coin_id: str):
        # Fetch comprehensive coin data
        # Map CMC response to standard format
        pass
    
    def get_tokenomics(self, coin_id: str):
        # Fetch and format tokenomics
        pass
```

### Step 2: Add to Config

Add your API credentials to `config.py`:

```python
COINMARKETCAP_API_KEY = "your_api_key_here"
```

### Step 3: Register Provider

In `services/data_service.py`, add your provider:

```python
from services.apis.coingecko import CoinGeckoProvider
from services.apis.coinmarketcap import CoinMarketCapProvider
from config import COINMARKETCAP_API_KEY

# Initialize with multiple providers
data_service = DataService(providers=[
    CoinGeckoProvider(),                    # Try first (free)
    CoinMarketCapProvider(COINMARKETCAP_API_KEY),  # Fallback
])
```

### Step 4: Test

```bash
cd backend
python3 -c "
from services.data_service import data_service

# Check all providers
health = data_service.check_provider_health()
print('Provider health:', health)

# Test fetching data (will try providers in order)
data = data_service.get_tokenomics('bitcoin')
print('Success:', data['name'])
"
```

## How Fallback Works

When you call `data_service.get_tokenomics('bitcoin')`:

1. **Tries CoinGecko** → If it works, done ✓
2. **If CoinGecko fails** (rate limit, down, etc.) → Tries CoinMarketCap
3. **If CoinMarketCap fails** → Tries next provider
4. **If all fail** → Returns aggregated error message

## Benefits

✅ **Zero downtime** - If one API is down, others work  
✅ **Rate limit protection** - Automatically switches APIs  
✅ **Easy to add** - Just create one new file per provider  
✅ **No code changes** - Existing routes/services work as-is  
✅ **Provider optimization** - Remembers last successful provider  

## Provider Priority

Providers are tried in the order you add them. Put:
- **Free APIs first** (CoinGecko)
- **Paid APIs as fallback** (CoinMarketCap)
- **Rate-limited APIs last**

## Response Format

All providers must return data in this standard format:

### Tokenomics Response
```python
{
    "name": "Bitcoin",
    "symbol": "BTC",
    "market_cap": 850000000000,
    "circulating_supply": 19500000,
    "total_supply": 21000000,
    "max_supply": 21000000
}
```

### Coin Data Response
Must include:
- `name`, `symbol`
- `market_data.market_cap.usd`
- `market_data.total_volume.usd`
- `market_data.circulating_supply`
- `links.repos_url.github` (optional)

## Monitoring

Check which provider is being used:

```python
# In your Flask routes
from services.data_service import data_service

@app.route('/api/health')
def health():
    return jsonify(data_service.check_provider_health())
```

## Next Steps

Recommended providers to add:
1. **CoinMarketCap** - More reliable, requires API key
2. **CryptoCompare** - Good for historical data
3. **Messari** - Great for on-chain metrics
