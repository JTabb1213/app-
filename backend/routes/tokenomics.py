"""
Tokenomics route
================
Serves supply & inflation data for a coin.

Data is pre-fetched on a weekly schedule by rating/tokenomics-collector and
stored in Redis (primary) and Postgres (cold-start fallback).
No external API calls are made at request time.
"""

from flask import Blueprint, jsonify
from services.tokenomics.tokenomics_service import get_tokenomics

tokenomics_bp = Blueprint("tokenomics", __name__)


@tokenomics_bp.route("/tokenomics/<coin_id>")
def tokenomics_route(coin_id: str):
    """
    GET /api/tokenomics/<coin_id>

    Returns the latest supply snapshot for the given CoinGecko coin_id.

    Example:
        GET /api/tokenomics/bitcoin
        GET /api/tokenomics/ethereum
    """
    data = get_tokenomics(coin_id)

    if data is None:
        return jsonify({
            "error": f"No tokenomics data found for '{coin_id}'.",
            "hint": (
                "Make sure the coin_id matches a CoinGecko id listed in "
                "rating/tokenomics-collector/coins.json and that the collector "
                "has run at least once."
            ),
        }), 404

    return jsonify(data), 200
