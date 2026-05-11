"""
Holder Diversity Collector — SQL storage
==========================================
Writes snapshots to the unified rating_snapshots table.
Reads all holder diversity snapshots on startup so Redis can be seeded.

Writes come from this collector only.
The backend reads via backend/services/holder_diversity/database.py.
"""

import json
import logging
from datetime import datetime
from typing import Optional

import psycopg2
import psycopg2.extras

import config

logger = logging.getLogger(__name__)

_METRIC_TYPE = "holder_diversity"

_conn = None


def _connect():
    conn = psycopg2.connect(config.DATABASE_URL)
    logger.info("[HolderDiversitySQL] Connected to PostgreSQL")
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


# ── Write ──────────────────────────────────────────────────────────────────────

def upsert_snapshot(snapshot: dict) -> bool:
    """
    Insert or update a holder diversity snapshot in rating_snapshots.

    Stores the full snapshot dict as JSONB data with metric_type='holder_diversity'.
    Uses ON CONFLICT DO UPDATE so repeated runs are idempotent.
    """
    coin_id = snapshot.get("coin_id", "").lower()
    chain = snapshot.get("chain", "").lower()
    if not coin_id or not chain:
        logger.error("upsert_snapshot: snapshot missing coin_id or chain")
        return False

    # Store full snapshot as JSONB data
    data_json = json.dumps(snapshot)
    snapshot_time = snapshot.get("snapshot_time")
    source = snapshot.get("source", "Covalent")

    sql = """
        INSERT INTO rating_snapshots
            (coin_id, metric_type, data, source, snapshot_time)
        VALUES (%s, %s, %s::jsonb, %s, %s)
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
        logger.debug(f"[HolderDiversitySQL] Upserted {coin_id}/{chain} to rating_snapshots")
        return True
    except Exception as e:
        logger.error(f"[HolderDiversitySQL] Error upserting {coin_id}/{chain}: {e}")
        try:
            _conn.rollback()
        except Exception:
            pass
        return False


# ── Read (used for cold-start Redis seeding) ───────────────────────────────────

def get_all_snapshots() -> list[dict]:
    """
    Return all holder diversity snapshots from rating_snapshots.
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

        logger.info(f"[HolderDiversitySQL] Loaded {len(snapshots)} snapshots from rating_snapshots")
        return snapshots
    except Exception as e:
        logger.error(f"[HolderDiversitySQL] Error reading snapshots: {e}")
        return []
