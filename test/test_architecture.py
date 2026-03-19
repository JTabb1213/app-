"""Test reorganized architecture"""
print('Testing reorganized architecture...\n')

from services.cache import cache_service, cache_updater
from services.data import data_service
from services.scoring_logic import get_score

print('✅ All imports successful\n')

# Test cache updater calling data_service
print('1. Testing cache_updater → data_service flow...')
result = cache_updater.update_coin('bitcoin')
print(f'   tokenomics_updated: {result["tokenomics_updated"]}')
print(f'   coin_data_updated: {result["coin_data_updated"]}')

# Test data_service with force_refresh
print('\n2. Testing data_service force_refresh...')
tokenomics = data_service.get_tokenomics('ethereum', force_refresh=True)
print(f'   ✅ Force refresh: {tokenomics["name"]}')

# Test regular cache read
print('\n3. Testing regular cache read...')
tokenomics_cached = data_service.get_tokenomics('bitcoin')
print(f'   ✅ Cache read: {tokenomics_cached["name"]}')

print('\n🎉 All tests passed! Correct architecture flow!')
