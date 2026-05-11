"""
Holder Diversity routes
=======================

GET /api/holder-diversity/<coin_id>
    Returns the latest holder snapshot from Redis or (if Redis is cold) SQL.
    Data is populated by the standalone rating/holder-diversity-collector service.

    Query params:
        chain  (str, default "ethereum")
"""

import logging
from flask import Blueprint, jsonify, request
from services.holder_diversity.holder_diversity_service import get_holder_diversity

logger = logging.getLogger(__name__)

holder_diversity_bp = Blueprint("holder_diversity", __name__)


@holder_diversity_bp.route("/holder-diversity/<coin_id>", methods=["GET"])
def get_holder_diversity_route(coin_id: str):
    """Return the holder snapshot for a coin from Redis or SQL."""
    chain = request.args.get("chain", "ethereum")

    logger.info(f"GET /holder-diversity/{coin_id}?chain={chain}")

    try:
        data = get_holder_diversity(coin_id.lower(), chain)

        if data is None:
            return jsonify({
                "error": f"No holder diversity data available for {coin_id} on {chain}.",
                "hint": "Data is collected weekly by the holder-diversity-collector service.",
            }), 404

        return jsonify(data), 200

    except Exception as e:
        logger.exception(f"[holder-diversity] GET error for {coin_id}: {e}")
        return jsonify({"error": str(e)}), 500
