from flask import Blueprint, jsonify
from services.data import data_service

tokenomics_bp = Blueprint("tokenomics", __name__)

@tokenomics_bp.route("/tokenomics/<coin_id>")
def tokenomics_route(coin_id):
    try:
        tokenomics = data_service.get_tokenomics(coin_id)
        return jsonify(tokenomics)
    except Exception as e:
        error_msg = str(e)
        # Check if it's a rate limit error
        if "rate limit" in error_msg.lower():
            return jsonify({"error": error_msg}), 429
        return jsonify({"error": error_msg}), 400
