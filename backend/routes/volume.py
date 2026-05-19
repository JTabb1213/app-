from flask import Blueprint, jsonify, request
from services.volume.main import get_volume
from services.volume.sources.redis_source import WINDOWS

volume_bp = Blueprint("volume", __name__)


@volume_bp.route("/volume/<coin_id>", methods=["GET"])
def volume(coin_id: str):
    window = request.args.get("window", "1h").lower()

    if window not in WINDOWS:
        return jsonify({
            "error": f"Unsupported window '{window}'. Valid: {', '.join(WINDOWS)}"
        }), 400

    data = get_volume(coin_id.lower(), window)

    if data is None:
        return jsonify({
            "error": "Volume data temporarily unavailable",
            "coin_id": coin_id,
        }), 503

    return jsonify(data)
