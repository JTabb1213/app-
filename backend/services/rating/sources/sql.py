"""
Rating service — SQL source
============================
Reads the pre-computed CCS score directly from Postgres.

Used as a fallback when Redis is cold/unavailable.
Table:  rating_scores  (see sql/rating_snapshots.sql)
"""

import json
import logging
import os
from typing import Optional

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

_conn = None


def _pg_connect():
    primary  = os.getenv("DATABASE_URL")
    fallback = os.getenv("DATABASE_URL_IPV4")
    try:
        return psycopg2.connect(primary, connect_timeout=5)
    except psycopg2.OperationalError as exc:
        if fallback and fallback != primary:
            logger.warning(f"[rating/sql] Primary unreachable ({exc}), trying IPv4 fallback")
            return psycopg2.connect(fallback, connect_timeout=5)
        raise


def _get_conn():
    global _conn
    try:
        if _conn is None or _conn.closed:
            raise psycopg2.OperationalError("no connection")
        _conn.cursor().execute("SELECT 1")
    except Exception:
        _conn = _pg_connect()
    return _conn


def get(coin_id: str) -> Optional[dict]:
    """
    Fetch the latest rating snapshot for *coin_id* from rating_scores.
    Returns None if no row exists or DB is unreachable.
    """
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    coin_id,
                    coin_symbol,
                    overall_score,
                    automated_score,
                    manual_validation,
                    risk_level,
                    security_transparency,
                    tokenomics_utility,
                    community_dev_activity,
                    public_discourse,
                    last_computed_at,
                    review_status
                FROM rating_scores
                WHERE coin_id = %s
                LIMIT 1
                """,
                (coin_id.lower(),),
            )
            row = cur.fetchone()
        if row is None:
            logger.debug(f"[rating/sql] No row for {coin_id}")
            return None
        # Convert RealDictRow to plain dict and serialize timestamps
        result = dict(row)
        # psycopg2 may return JSONB columns as strings — parse them
        for jsonb_col in ("security_transparency", "tokenomics_utility", "community_dev_activity", "public_discourse"):
            val = result.get(jsonb_col)
            if isinstance(val, str):
                try:
                    result[jsonb_col] = json.loads(val)
                except Exception:
                    pass
        if result.get("last_computed_at"):
            result["last_computed_at"] = result["last_computed_at"].isoformat()
        return result
    except Exception as exc:
        logger.error(f"[rating/sql] Error fetching {coin_id}: {exc}")
        global _conn
        try:
            if _conn:
                _conn.close()
        except Exception:
            pass
        _conn = None
        return None
