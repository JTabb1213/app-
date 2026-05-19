"""
Rating route
=============
GET /api/rating/<coin_id>

Returns the pre-computed CCS score for a coin.
Data is written by the rating/score-orchestrator and stored in Redis
(primary) and Postgres (fallback).

Response shape (200):
{
    "coin_id":               "bitcoin",
    "coin_symbol":           "BTC",
    "overall_score":         82.0,
    "automated_score":       57.0,
    "manual_validation":     25.0,
    "risk_level":            "Low",
    "security_transparency": { "score": 30, "max": 35, "metrics": { ... } },
    "tokenomics_utility":    { "score": 16, "max": 20, "metrics": { ... } },
    "community_dev_activity":{ "score": 8,  "max": 15, "metrics": { ... } },
    "public_discourse":      { "score": 3,  "max": 5,  "metrics": { ... } },
    "last_computed_at":      "2026-05-11T00:00:00+00:00",
    "review_status":         "complete",
    "_source":               "redis"   // "redis" | "sql"
}
"""

import logging
from flask import Blueprint, jsonify
from services.rating.main import get_rating

logger    = logging.getLogger(__name__)
rating_bp = Blueprint("rating", __name__)


@rating_bp.route("/rating/<coin_id>", methods=["GET"])
def rating_route(coin_id: str):
    """
    GET /api/rating/<coin_id>

    Returns the latest CCS rating snapshot for the given coin.
    Reads from Redis first, falls back to SQL if cache is cold.
    """
    logger.info(f"GET /rating/{coin_id}")
    data = get_rating(coin_id)
    if data is None:
        return jsonify({
            "error": f"No rating data found for '{coin_id}'.",
            "hint": (
                "Ensure the coin is listed in rating/collectors/*/coins.json "
                "and the score-orchestrator has completed at least one run."
            ),
        }), 404
    return jsonify(data), 200
