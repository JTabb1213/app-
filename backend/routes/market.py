from flask import Blueprint, jsonify
from services.market.main import get_market

market_bp = Blueprint("market", __name__)


@market_bp.route("/market/<coin_id>", methods=["GET"])
def market(coin_id: str):
    data = get_market(coin_id.lower())
    if data is None:
        return jsonify({"error": "Market data unavailable", "coin_id": coin_id}), 404

    return jsonify({
        "coin_id":            data.get("coin_id", coin_id),
        "market_cap_usd":     data.get("market_cap_usd"),
        "circulating_supply": data.get("circulating_supply"),
        "last_fetched_at":    data.get("last_fetched_at"),
        "_source":            data.get("_source"),
    })
