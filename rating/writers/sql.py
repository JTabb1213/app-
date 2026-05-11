"""
Writers: SQL
=============
All database operations for the score orchestrator.

Responsibilities:
  - Read manual_validation for a coin (set by analysts, default 25)
  - Read previous GitHub snapshot (for delta_commits calculation)
  - Upsert final score row into rating_scores
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

_conn = None


def init(database_url: str):
    """Open (or re-open) the database connection."""
    global _conn
    _conn = psycopg2.connect(database_url)
    logger.info("[SQL] Connected to PostgreSQL")


def _get_conn():
    global _conn
    try:
        if _conn is None or _conn.closed:
            raise psycopg2.OperationalError("no connection")
        _conn.cursor().execute("SELECT 1")
    except Exception:
        raise RuntimeError("SQL connection is not initialised — call writers.sql.init() first")
    return _conn


# ── Reads ──────────────────────────────────────────────────────────────────────

def get_manual_validation(coin_id: str) -> float:
    """
    Return the manually set analyst score for a coin.
    Defaults to 25 (full marks) if the coin has no row yet.
    """
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT manual_validation FROM rating_scores WHERE coin_id = %s",
                (coin_id.lower(),),
            )
            row = cur.fetchone()
            return float(row[0]) if row else 25.0
    except Exception as exc:
        logger.error(f"[SQL] get_manual_validation({coin_id}): {exc} — using default 25")
        return 25.0


def get_previous_github_snapshot(coin_id: str) -> Optional[dict]:
    """
    Return the community_dev_activity JSONB for a coin from the last run.
    Used to compute delta_commits = current_total - previous_total.
    """
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT community_dev_activity FROM rating_scores WHERE coin_id = %s",
                (coin_id.lower(),),
            )
            row = cur.fetchone()
            if row and row["community_dev_activity"]:
                val = row["community_dev_activity"]
                return val if isinstance(val, dict) else json.loads(val)
            return None
    except Exception as exc:
        logger.error(f"[SQL] get_previous_github_snapshot({coin_id}): {exc}")
        return None


# ── Writes ─────────────────────────────────────────────────────────────────────

def upsert_rating_score(score_row: dict) -> bool:
    """
    Insert or update a row in rating_scores.

    Expected keys: coin_id, coin_symbol, overall_score, automated_score,
    manual_validation, risk_level, security_transparency, tokenomics_utility,
    community_dev_activity, public_discourse
    """
    coin_id = score_row.get("coin_id", "").lower()
    if not coin_id:
        logger.error("[SQL] upsert_rating_score: missing coin_id")
        return False

    def _j(v):
        return json.dumps(v) if isinstance(v, dict) else (v or "{}")

    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO rating_scores (
                    coin_id, coin_symbol,
                    overall_score, automated_score, manual_validation,
                    risk_level,
                    security_transparency, tokenomics_utility,
                    community_dev_activity, public_discourse,
                    last_computed_at, review_status
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb,
                    NOW(), 'pending'
                )
                ON CONFLICT (coin_id) DO UPDATE SET
                    coin_symbol            = EXCLUDED.coin_symbol,
                    overall_score          = EXCLUDED.overall_score,
                    automated_score        = EXCLUDED.automated_score,
                    manual_validation      = EXCLUDED.manual_validation,
                    risk_level             = EXCLUDED.risk_level,
                    security_transparency  = EXCLUDED.security_transparency,
                    tokenomics_utility     = EXCLUDED.tokenomics_utility,
                    community_dev_activity = EXCLUDED.community_dev_activity,
                    public_discourse       = EXCLUDED.public_discourse,
                    last_computed_at       = NOW(),
                    updated_at             = NOW()
                """,
                (
                    coin_id,
                    score_row.get("coin_symbol", ""),
                    score_row["overall_score"],
                    score_row["automated_score"],
                    score_row["manual_validation"],
                    score_row.get("risk_level"),
                    _j(score_row.get("security_transparency")),
                    _j(score_row.get("tokenomics_utility")),
                    _j(score_row.get("community_dev_activity")),
                    _j(score_row.get("public_discourse")),
                ),
            )
        conn.commit()
        logger.debug(f"[SQL] Upserted rating_scores for {coin_id}")
        return True
    except Exception as exc:
        logger.error(f"[SQL] upsert_rating_score({coin_id}): {exc}")
        try:
            _get_conn().rollback()
        except Exception:
            pass
        return False
