from flask import Blueprint, jsonify
from services.news.main import get_news

news_bp = Blueprint("news", __name__)


@news_bp.route("/news/<coin_id>", methods=["GET"])
def news(coin_id: str):
    articles = get_news(coin_id.lower())
    if not articles:
        return jsonify({"error": "News unavailable", "coin_id": coin_id}), 404

    return jsonify({
        "coin_id":  coin_id,
        "articles": articles,
    })
