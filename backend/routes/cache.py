"""
Cache management routes.
Endpoints for updating and monitoring the Redis cache, including alias management.
"""

from flask import Blueprint, jsonify, request
from services.cache import cache_updater
from services.cache.service import CacheService
from services.cache.alias_updater import AliasUpdater

cache_bp = Blueprint("cache", __name__)

# Initialize services
cache_service = CacheService()
alias_updater_service = AliasUpdater(cache_service)


@cache_bp.route("/update-cache", methods=["POST"])
def update_cache():
    """
    Manually trigger cache updates for specific coins or batch updates.
    
    Request body options:
    {
        "coin_id": "bitcoin"  // Update a single coin
    }
    OR
    {
        "coin_ids": ["bitcoin", "ethereum", "solana"]  // Update multiple coins
    }
    OR
    {
        "popular": true,  // Update top popular coins
        "limit": 20       // Number of popular coins to update (optional)
    }
    """
    try:
        data = request.get_json() or {}
        
        # Single coin update
        if "coin_id" in data:
            coin_id = data["coin_id"]
            result = cache_updater.update_coin(coin_id)
            
            if result.get("tokenomics_updated") or result.get("coin_data_updated"):
                return jsonify({
                    "success": True,
                    "message": f"Cache updated for {coin_id}",
                    "result": result
                }), 200
            else:
                return jsonify({
                    "success": False,
                    "message": f"Failed to update cache for {coin_id}",
                    "result": result
                }), 500
        
        # Multiple coins update
        elif "coin_ids" in data:
            coin_ids = data["coin_ids"]
            if not isinstance(coin_ids, list):
                return jsonify({
                    "error": "coin_ids must be an array"
                }), 400
            
            result = cache_updater.update_multiple_coins(coin_ids)
            return jsonify({
                "success": True,
                "message": f"Batch update complete: {result['succeeded']} succeeded, {result['failed']} failed",
                "result": result
            }), 200
        
        # Popular coins update
        elif "popular" in data and data["popular"]:
            limit = data.get("limit", 20)
            result = cache_updater.update_popular_coins(limit)
            return jsonify({
                "success": True,
                "message": f"Updated {result['succeeded']} popular coins",
                "result": result
            }), 200
        
        else:
            return jsonify({
                "error": "Must provide 'coin_id', 'coin_ids', or 'popular' parameter"
            }), 400
            
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@cache_bp.route("/cache-stats", methods=["GET"])
def cache_stats():
    """
    Get cache statistics and health information.
    """
    try:
        stats = cache_updater.get_cache_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@cache_bp.route("/update-aliases", methods=["POST"])
def update_aliases():
    """
    Trigger an update of all coin aliases from CoinGecko.
    Fetches the complete coins list and populates alias mappings.
    """
    try:
        result = alias_updater_service.update_all_aliases()
        
        if result["success"]:
            return jsonify({
                "success": True,
                "message": "Aliases updated successfully",
                "aliases_updated": result["aliases_updated"],
                "coins_processed": result["coins_processed"]
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": result.get("error", "Unknown error")
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@cache_bp.route("/alias/<search_term>", methods=["GET"])
def get_alias(search_term: str):
    """
    Resolve a search term to its canonical coin ID.
    
    Args:
        search_term: Coin name, symbol, or ID to resolve
    """
    try:
        canonical_id = cache_service.get_alias(search_term)
        
        if canonical_id:
            return jsonify({
                "success": True,
                "search_term": search_term,
                "canonical_id": canonical_id
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": f"No alias found for '{search_term}'"
            }), 404
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
