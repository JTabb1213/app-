"""
Market service — SQL source
============================
Reads / writes market data in the market_data table.

Schema (create with sql/market_data.sql):
    CREATE TABLE IF NOT EXISTS market_data (
        coin_id            TEXT PRIMARY KEY,
        market_cap_usd     NUMERIC,
        circulating_supply NUMERIC,
        last_fetched_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
"""

import logging
import os
from datetime import timezone
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
            logger.warning("[market/sql] Primary unreachable (%s), trying IPv4 fallback", exc)
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
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT coin_id, price_usd, market_cap, circulating_supply,
                       volume_24h, updated_at
                FROM market_data
                WHERE coin_id = %s
                """,
                (coin_id,),
            )
            row = cur.fetchone()
        if not row:
            return None

        d = dict(row)
        if d.get("updated_at"):
            ts = d.pop("updated_at")
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            d["last_fetched_at"] = ts.isoformat()

        for col in ("price_usd", "market_cap", "circulating_supply", "volume_24h"):
            d[col] = float(d[col]) if d.get(col) is not None else None
        # backward-compat alias used by the frontend
        d["market_cap_usd"] = d.get("market_cap")
        d["_source"] = "sql"
        return d

    except Exception as exc:
        logger.warning("[market/sql] Read failed for %s: %s", coin_id, exc)
        return None


def upsert(coin_id: str, market_cap_usd: float, circulating_supply: float) -> None:
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO market_data (coin_id, market_cap, circulating_supply, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (coin_id) DO UPDATE
                    SET market_cap         = EXCLUDED.market_cap,
                        circulating_supply = EXCLUDED.circulating_supply,
                        updated_at         = EXCLUDED.updated_at
                """,
                (coin_id, market_cap_usd, circulating_supply),
            )
        conn.commit()
    except Exception as exc:
        logger.warning("[market/sql] Upsert failed for %s: %s", coin_id, exc)
        try:
            _conn.rollback()
        except Exception:
            pass
