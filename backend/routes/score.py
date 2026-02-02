from flask import Blueprint, jsonify
from services.scoring_service import get_score

score_bp = Blueprint("score", __name__)

@score_bp.route("/score/<coin_id>")
def score_route(coin_id):
    try:
        score = get_score(coin_id)
        return jsonify(score)
    except Exception as e:
        error_msg = str(e)
        # Check if it's a rate limit error
        if "rate limit" in error_msg.lower():
            return jsonify({"error": error_msg}), 429
        return jsonify({"error": error_msg}), 400
