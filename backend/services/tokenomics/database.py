"""
Tokenomics — read-only database layer.
Fetches the latest tokenomics snapshot from the rating_snapshots table.
Writes are handled exclusively by rating/tokenomics-collector.
"""

import json
import logging
from datetime import datetime
from typing import Optional

import psycopg2
import psycopg2.extras

from services.tokenomics.config import DATABASE_URL

logger = logging.getLogger(__name__)

_METRIC_TYPE = "tokenomics"

_conn = None


def _connect():
    conn = psycopg2.connect(DATABASE_URL)
    logger.info("[TokenomicsDB] Connected to PostgreSQL")
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


def get_latest_snapshot(coin_id: str) -> Optional[dict]:
    """
    Return the most recent tokenomics snapshot for a coin.
    Returns None if no row exists yet.
    """
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT data, snapshot_time
                FROM rating_snapshots
                WHERE coin_id = %s AND metric_type = %s
                LIMIT 1
                """,
                (coin_id.lower(), _METRIC_TYPE),
            )
            row = cur.fetchone()
            if not row:
                return None

            data = row["data"]
            if isinstance(data, str):
                data = json.loads(data)

            # Normalise datetime fields to ISO strings
            for key in ("snapshot_time",):
                if key in data and isinstance(data[key], datetime):
                    data[key] = data[key].isoformat()

            return data
    except Exception as e:
        logger.error(f"[TokenomicsDB] Error reading snapshot for {coin_id}: {e}")
        return None
