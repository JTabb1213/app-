"""
Volume API — real-time buy/sell volume from Redis.

GET /api/volume/<coin_id>?window=5m
GET /api/volume/all?window=5m
"""

import json
import time
from flask import Blueprint, jsonify, request
import redis

from config import REDIS_URL

volume_bp = Blueprint("volume", __name__)

WINDOW_SECONDS = {
    "5m": 300,
    "30m": 1800,
    "4h": 14400,
    "24h": 86400,
}

_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


def _sum_volume(coin_id: str, window: str) -> dict | None:
    r = _get_redis()
    key = f"vol:{coin_id}"

    if not r.exists(key):
        return None

    seconds = WINDOW_SECONDS.get(window, 300)
    cutoff = int(time.time()) - seconds

    fields = r.hgetall(key)
    buy = 0.0
    sell = 0.0
    exchanges_seen = set()
    for ts_str, val_raw in fields.items():
        try:
            ts = int(ts_str)
        except ValueError:
            continue
        if ts < cutoff:
            continue
        try:
            val = json.loads(val_raw)
            buy += val.get("b", 0.0)
            sell += val.get("s", 0.0)
            for ex in val.get("ex", []):
                exchanges_seen.add(ex)
        except (json.JSONDecodeError, TypeError):
            continue

    total = buy + sell
    return {
        "coin_id": coin_id,
        "window": window,
        "buy_volume_usd": round(buy, 2),
        "sell_volume_usd": round(sell, 2),
        "total_volume_usd": round(total, 2),
        "buy_pct": round(buy / total * 100, 1) if total > 0 else 50.0,
        "exchange_count": len(exchanges_seen),
    }


@volume_bp.route("/volume/<coin_id>", methods=["GET"])
def get_volume(coin_id: str):
    window = request.args.get("window", "5m")
    if window not in WINDOW_SECONDS:
        return jsonify({"error": f"Invalid window. Use: {list(WINDOW_SECONDS.keys())}"}), 400

    result = _sum_volume(coin_id, window)
    if result is None:
        return jsonify({"error": f"No volume data for {coin_id}"}), 404

    return jsonify(result)


@volume_bp.route("/volume/all", methods=["GET"])
def get_all_volume():
    window = request.args.get("window", "5m")
    if window not in WINDOW_SECONDS:
        return jsonify({"error": f"Invalid window. Use: {list(WINDOW_SECONDS.keys())}"}), 400

    r = _get_redis()
    cursor = 0
    results = []
    while True:
        cursor, keys = r.scan(cursor, match="vol:*", count=200)
        for key in keys:
            coin_id = key.removeprefix("vol:")
            vol = _sum_volume(coin_id, window)
            if vol and vol["total_volume_usd"] > 0:
                results.append(vol)
        if cursor == 0:
            break

    results.sort(key=lambda x: x["total_volume_usd"], reverse=True)
    return jsonify({"window": window, "count": len(results), "data": results})
