"""
Tokenomics Collector — SQL storage
====================================
Writes snapshots to the rating_snapshots table.
Reads all tokenomics snapshots on startup so Redis can be seeded.

Writes come from this collector only.
The backend reads via backend/services/tokenomics/database.py.
"""

import json
import logging
from datetime import datetime
from typing import Optional

import psycopg2
import psycopg2.extras

import config

logger = logging.getLogger(__name__)

_METRIC_TYPE = "tokenomics"

_conn = None


def _connect():
    conn = psycopg2.connect(config.DATABASE_URL)
    logger.info("[TokenomicsSQL] Connected to PostgreSQL")
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


def upsert_snapshot(snapshot: dict) -> bool:
    """
    Insert or update a tokenomics snapshot in rating_snapshots.

    Uses ON CONFLICT DO UPDATE so repeated runs are idempotent.
    """
    coin_id = snapshot.get("coin_id", "").lower()
    if not coin_id:
        logger.error("upsert_snapshot: snapshot missing coin_id")
        return False

    # Store the full snapshot dict as JSONB data
    data_json = json.dumps(snapshot)
    snapshot_time = snapshot.get("snapshot_time")
    source = snapshot.get("source", "CoinGecko")

    sql = """
        INSERT INTO rating_snapshots
            (coin_id, metric_type, data, source, snapshot_time)
        VALUES
            (%s, %s, %s::jsonb, %s, %s)
        ON CONFLICT (coin_id, metric_type)
        DO UPDATE SET
            data          = EXCLUDED.data,
            source        = EXCLUDED.source,
            snapshot_time = EXCLUDED.snapshot_time
    """
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute(sql, (coin_id, _METRIC_TYPE, data_json, source, snapshot_time))
        conn.commit()
        logger.debug(f"[TokenomicsSQL] Upserted snapshot for {coin_id}")
        return True
    except Exception as e:
        logger.error(f"[TokenomicsSQL] Error upserting {coin_id}: {e}")
        try:
            _conn.rollback()
        except Exception:
            pass
        return False


def get_all_snapshots() -> list[dict]:
    """
    Return all tokenomics snapshots from rating_snapshots.
    Used at startup to seed Redis from the database.
    """
    sql = """
        SELECT data, snapshot_time
        FROM rating_snapshots
        WHERE metric_type = %s
    """
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (_METRIC_TYPE,))
            rows = cur.fetchall()

        snapshots = []
        for row in rows:
            data = row["data"]
            if isinstance(data, str):
                data = json.loads(data)
            # Ensure snapshot_time is a string
            if isinstance(data.get("snapshot_time"), datetime):
                data["snapshot_time"] = data["snapshot_time"].isoformat()
            snapshots.append(data)

        logger.info(f"[TokenomicsSQL] Loaded {len(snapshots)} snapshots from DB")
        return snapshots
    except Exception as e:
        logger.error(f"[TokenomicsSQL] Error reading snapshots: {e}")
        return []
