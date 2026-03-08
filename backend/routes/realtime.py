"""
Real-time market data routes.
Bulk-updates the tokenomics cache with data from CoinGecko /markets endpoint.
"""

from flask import Blueprint, jsonify, request
from services.cache.realtime_updater import realtime_cache_updater

realtime_bp = Blueprint("realtime", __name__)


@realtime_bp.route("/realtime/update", methods=["POST"])
def update_realtime_cache():
    """
    Fetch top coins from CoinGecko /markets and cache their tokenomics data
    with a 2-minute TTL. This bulk-populates the cache so the frontend gets
    live data via the existing /api/tokenomics/{id} endpoint.

    Optional body: { "limit": 50 }
    """
    try:
        limit = 50
        if request.json and "limit" in request.json:
            limit = int(request.json["limit"])

        result = realtime_cache_updater.update_top_coins(limit=limit)

        if result.get("success"):
            return jsonify({
                "success": True,
                "message": f"Cached tokenomics for {result['cached']} coins (2-min TTL)",
                **result,
            }), 200
        else:
            return jsonify(result), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

