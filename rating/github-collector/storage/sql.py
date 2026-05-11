"""
GitHub Collector — SQL storage
================================
Writes snapshots to rating_snapshots.
Reads previous snapshots on startup to seed Redis and to compute commit deltas.

Key behaviour:
  - On each run, the previous total_commit_count is read from SQL.
  - delta_commits = current_total - previous_total  →  "commits this period"
  - The new snapshot (with current_total) replaces the old row.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import psycopg2
import psycopg2.extras

import config

logger = logging.getLogger(__name__)

_METRIC_TYPE = "github"
_conn = None


def _connect():
    conn = psycopg2.connect(config.DATABASE_URL)
    logger.info("[GitHubSQL] Connected to PostgreSQL")
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


def get_previous_snapshot(coin_id: str) -> Optional[dict]:
    """
    Return the most recently stored snapshot for a coin, or None.
    Used to compute the commit delta between runs.
    """
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT data FROM rating_snapshots
                WHERE coin_id = %s AND metric_type = %s
                LIMIT 1
                """,
                (coin_id.lower(), _METRIC_TYPE),
            )
            row = cur.fetchone()
            if row:
                return json.loads(row["data"]) if isinstance(row["data"], str) else row["data"]
            return None
    except Exception as exc:
        logger.error(f"[GitHubSQL] get_previous_snapshot({coin_id}): {exc}")
        return None


def upsert_snapshot(snapshot: dict) -> bool:
    """
    Insert or update a GitHub snapshot row in rating_snapshots.
    """
    coin_id = snapshot.get("coin_id", "").lower()
    if not coin_id:
        logger.error("upsert_snapshot: missing coin_id")
        return False

    data_json      = json.dumps(snapshot)
    snapshot_time  = snapshot.get("snapshot_time", datetime.now(timezone.utc).isoformat())
    source         = snapshot.get("source", "GitHub")

    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO rating_snapshots
                    (coin_id, metric_type, data, source, snapshot_time)
                VALUES (%s, %s, %s::jsonb, %s, %s)
                ON CONFLICT (coin_id, metric_type)
                DO UPDATE SET
                    data          = EXCLUDED.data,
                    source        = EXCLUDED.source,
                    snapshot_time = EXCLUDED.snapshot_time,
                    updated_at    = NOW()
                """,
                (coin_id, _METRIC_TYPE, data_json, source, snapshot_time),
            )
        conn.commit()
        logger.debug(f"[GitHubSQL] Upserted {coin_id}")
        return True
    except Exception as exc:
        logger.error(f"[GitHubSQL] upsert_snapshot({coin_id}): {exc}")
        try:
            _get_conn().rollback()
        except Exception:
            pass
        return False


def load_all_snapshots() -> list[dict]:
    """
    Return all stored GitHub snapshots. Used at startup to seed Redis.
    """
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT data FROM rating_snapshots WHERE metric_type = %s",
                (_METRIC_TYPE,),
            )
            rows = cur.fetchall()
        return [
            (json.loads(r["data"]) if isinstance(r["data"], str) else r["data"])
            for r in rows
        ]
    except Exception as exc:
        logger.error(f"[GitHubSQL] load_all_snapshots: {exc}")
        return []
