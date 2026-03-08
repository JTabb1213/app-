"""
Database routes – CRUD endpoints for the coins table (static data).
"""

from flask import Blueprint, jsonify, request
from services.database.reader import coin_reader
from services.database.writer import coin_writer

database_bp = Blueprint("database", __name__)


# ------------------------------------------------------------------
# READ endpoints
# ------------------------------------------------------------------

@database_bp.route("/coins", methods=["GET"])
def list_coins():
    """
    List coins from the database.

    Query params:
        page  (int, default 1)
        per_page (int, default 50)
        search (str, optional) – filter by name/symbol/id
    """
    try:
        search = request.args.get("search")
        if search:
            coins = coin_reader.search_coins(search, limit=int(request.args.get("per_page", 50)))
            return jsonify({"coins": coins}), 200

        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 50))
        result = coin_reader.get_all_coins(page=page, per_page=per_page)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@database_bp.route("/coins/top", methods=["GET"])
def top_coins():
    """Return the top N coins by market_cap_rank from the DB."""
    try:
        limit = int(request.args.get("limit", 50))
        coins = coin_reader.get_top_coins(limit)
        return jsonify({"coins": coins}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@database_bp.route("/coins/<coin_id>", methods=["GET"])
def get_coin(coin_id: str):
    """Return a single coin's static data from the DB.
    On a cache miss, fetches from CoinGecko, populates the DB, and returns the result.
    """
    try:
        # Resolve aliases first (e.g. "ada" → "cardano", "btc" → "bitcoin")
        from services.cache import cache_service
        canonical_id = cache_service.get_alias(coin_id) or coin_id.lower()

        # Try DB with canonical id
        coin = coin_reader.get_coin(canonical_id)
        if coin:
            return jsonify(coin), 200

        # DB miss – fetch full coin data from CoinGecko and auto-populate
        print(f"[DB Route] '{coin_id}' not in DB, fetching from CoinGecko...")
        from services.apis.coingecko import CoinGeckoProvider
        from services.database.writer import _map_full_coin_data

        provider = CoinGeckoProvider()
        raw = provider.get_coin_data(canonical_id)
        mapped = _map_full_coin_data(raw)
        result = coin_writer.upsert_coin(mapped)
        print(f"[DB Route] ✓ Auto-populated DB for {mapped.get('id')}")
        return jsonify(result), 200

    except Exception as e:
        error_msg = str(e)
        if "rate limit" in error_msg.lower():
            return jsonify({"error": error_msg}), 429
        if "not found" in error_msg.lower():
            return jsonify({"error": f"Coin '{coin_id}' not found"}), 404
        return jsonify({"error": error_msg}), 500


# ------------------------------------------------------------------
# WRITE endpoints
# ------------------------------------------------------------------

@database_bp.route("/coins", methods=["POST"])
def add_coin():
    """
    Upsert a single coin.

    Body: JSON with at least { "id", "symbol", "name" }.
    """
    try:
        data = request.get_json()
        if not data or "id" not in data:
            return jsonify({"error": "Request body must include at least 'id'"}), 400

        result = coin_writer.upsert_coin(data)
        return jsonify({"success": True, "coin": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@database_bp.route("/coins/<coin_id>", methods=["DELETE"])
def delete_coin(coin_id: str):
    """Delete a coin from the database."""
    try:
        deleted = coin_writer.delete_coin(coin_id)
        if deleted:
            return jsonify({"success": True, "message": f"Deleted {coin_id}"}), 200
        return jsonify({"error": f"Coin '{coin_id}' not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------------------------------------------------------
# Populate from CoinGecko
# ------------------------------------------------------------------

@database_bp.route("/coins/populate", methods=["POST"])
def populate_coins():
    """
    Fetch top 50 coins from CoinGecko /coins/markets and upsert their
    static fields into the database.
    """
    try:
        from services.apis.coingecko_markets import coingecko_markets

        limit = int(request.json.get("limit", 50)) if request.json else 50
        raw = coingecko_markets.fetch_top_coins(per_page=limit)
        result = coin_writer.upsert_coins_from_market_data(raw)
        return jsonify({"success": True, **result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
