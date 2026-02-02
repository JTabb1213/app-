from flask import Blueprint, jsonify
from services.tokenomics_service import get_tokenomics

tokenomics_bp = Blueprint("tokenomics", __name__)

@tokenomics_bp.route("/tokenomics/<coin_id>")
def tokenomics_route(coin_id):
    try:
        tokenomics = get_tokenomics(coin_id)
        return jsonify(tokenomics)
    except Exception as e:
        error_msg = str(e)
        # Check if it's a rate limit error
        if "rate limit" in error_msg.lower():
            return jsonify({"error": error_msg}), 429
        return jsonify({"error": error_msg}), 400
