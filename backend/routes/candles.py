"""
Candles API — historical OHLCV candlestick data from Postgres.

GET /api/candles/<coin_id>?resolution=1h&limit=200
"""

from flask import Blueprint, jsonify, request
import psycopg2
import psycopg2.extras
import os

candles_bp = Blueprint("candles", __name__)

VALID_RESOLUTIONS = {
    "1m": "price_candles_1m",
    "5m": "price_candles_5m",
    "1h": "price_candles_1h",
    "1d": "price_candles_1d",
}

_conn = None


def _get_conn():
    global _conn
    try:
        if _conn is None or _conn.closed:
            _conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        # Test connection is alive
        _conn.cursor().execute("SELECT 1")
    except Exception:
        _conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    return _conn


@candles_bp.route("/candles/<coin_id>", methods=["GET"])
def get_candles(coin_id: str):
    resolution = request.args.get("resolution", "1h")
    limit = min(int(request.args.get("limit", 200)), 1000)

    if resolution not in VALID_RESOLUTIONS:
        return jsonify({"error": f"Invalid resolution. Use: {list(VALID_RESOLUTIONS.keys())}"}), 400

    table = VALID_RESOLUTIONS[resolution]

    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT bucket, open, high, low, close, volume, exchange_count, tick_count
                FROM {table}
                WHERE coin_id = %s
                ORDER BY bucket DESC
                LIMIT %s
                """,
                (coin_id, limit),
            )
            rows = cur.fetchall()
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    if not rows:
        return jsonify({"error": f"No candle data for {coin_id} at {resolution}"}), 404

    # Return in chronological order (chart libraries expect oldest→newest)
    candles = []
    for row in reversed(rows):
        candles.append({
            # lightweight-charts expects 'time' as a UNIX timestamp (seconds)
            "time": int(row["bucket"].timestamp()) if hasattr(row["bucket"], "timestamp")
                    else int(__import__("datetime").datetime.combine(row["bucket"], __import__("datetime").time()).timestamp()),
            "open":   float(row["open"]),
            "high":   float(row["high"]),
            "low":    float(row["low"]),
            "close":  float(row["close"]),
            "volume": float(row["volume"]),
        })

    return jsonify({
        "coin_id": coin_id,
        "resolution": resolution,
        "count": len(candles),
        "candles": candles,
    })
