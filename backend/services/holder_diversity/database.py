"""
Holder Diversity - read-only database layer.
Fetches the latest snapshot from the rating_snapshots table.
Writes are handled exclusively by rating/holder-diversity-collector.
"""

import json
import logging
import psycopg2
import psycopg2.extras
from datetime import datetime
from typing import Optional

from services.holder_diversity.config import DATABASE_URL

logger = logging.getLogger(__name__)

_conn = None


def _connect():
    conn = psycopg2.connect(DATABASE_URL)
    logger.info("[HolderDiversityDB] Connected to PostgreSQL")
    return conn


def _get_conn():
    global _conn
    try:
        if _conn is None or _conn.closed:
            raise psycopg2.OperationalError("no connection")
        _conn.cursor().execute("SELECT 1")
    except Exception:
        _conn = _connect()
    return _conn


def get_latest_snapshot(coin_id: str, chain: str) -> Optional[dict]:
    """
    Return the most recent holder diversity snapshot for a coin+chain.
    Returns None if the table has no row for this coin/chain yet.
    """
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT data FROM rating_snapshots WHERE coin_id = %s AND metric_type = %s LIMIT 1",
                (coin_id.lower(), "holder_diversity"),
            )
            row = cur.fetchone()
            if not row:
                return None
            data = row["data"]
            if isinstance(data, str):
                data = json.loads(data)
            # Convert datetime to ISO string if needed
            for key in ("snapshot_time", "created_at", "updated_at"):
                if key in data and isinstance(data[key], datetime):
                    data[key] = data[key].isoformat()
            return data
    except Exception as e:
        logger.error(f"[HolderDiversityDB] Error reading snapshot for {coin_id}/{chain}: {e}")
        return None
