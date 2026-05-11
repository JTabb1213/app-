"""
Candles API — historical OHLCV candlestick data from Postgres.

GET /api/candles/<coin_id>?resolution=1h&limit=200
"""

import logging
import os

import psycopg2
import psycopg2.extras
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

candles_bp = Blueprint("candles", __name__)

VALID_RESOLUTIONS = {
    "1m":     "price_candles_1m",
    "5m":     "price_candles_5m",
    "1h":     "price_candles_1h",
    "1d":     "price_candles_1d",
    "1w":     "price_candles_1w",
    "1month": "price_candles_1month",
}

_conn = None


def _pg_connect():
    """Open a new Postgres connection, trying IPv4 fallback if IPv6 fails."""
    primary = os.getenv("DATABASE_URL")
    fallback = os.getenv("DATABASE_URL_IPV4")

    try:
        logger.info("Candles: connecting to Postgres (primary)…")
        conn = psycopg2.connect(primary)
        logger.info("Candles: connected to Postgres")
        return conn
    except psycopg2.OperationalError as e:
        if fallback and fallback != primary:
            logger.warning(f"Candles: primary DB unreachable ({e}), trying IPv4 fallback…")
            conn = psycopg2.connect(fallback)
            logger.info("Candles: connected to Postgres via IPv4 fallback")
            return conn
        raise


def _get_conn():
    """Return a live DB connection, reconnecting (with fallback) if dropped."""
    global _conn
    try:
        if _conn is None or _conn.closed:
            raise psycopg2.OperationalError("no connection")
        # Liveness check
        _conn.cursor().execute("SELECT 1")
    except Exception as e:
        if _conn is not None and not _conn.closed:
            logger.warning(f"Candles: DB connection lost ({e}), reconnecting…")
        _conn = _pg_connect()
    return _conn


@candles_bp.route("/candles/<coin_id>", methods=["GET"])
def get_candles(coin_id: str):
    resolution = request.args.get("resolution", "1h")
    limit = min(int(request.args.get("limit", 200)), 1000)

    logger.info(f"GET /candles/{coin_id} resolution={resolution} limit={limit}")

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
        logger.error(f"Candles DB error for {coin_id}/{resolution}: {e}")
        # Reset so the next request triggers a fresh connect attempt
        global _conn
        try:
            if _conn:
                _conn.close()
        except Exception:
            pass
        _conn = None
        return jsonify({"error": str(e)}), 500

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
