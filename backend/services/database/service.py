"""
PostgreSQL database service.
Manages the connection pool to the Supabase-hosted Postgres database.
"""

import psycopg2
from psycopg2 import pool, extras
from typing import Optional
from config import DATABASE_URL


class DatabaseService:
    """
    Manages a PostgreSQL connection pool.
    Connection is deferred until the first actual database call so that
    a cold/unreachable Postgres does not crash the Flask worker at startup.
    """

    def __init__(self, database_url: str = DATABASE_URL, min_conn: int = 1, max_conn: int = 10):
        self.database_url = database_url
        self._min_conn = min_conn
        self._max_conn = max_conn
        self._pool: Optional[pool.SimpleConnectionPool] = None

    def _ensure_connected(self):
        """Lazily create the connection pool on first use."""
        if self._pool is not None:
            return
        try:
            self._pool = pool.SimpleConnectionPool(
                self._min_conn,
                self._max_conn,
                self.database_url,
            )
            # Quick connectivity check
            conn = self._pool.getconn()
            conn.cursor().execute("SELECT 1")
            self._pool.putconn(conn)
            print("[DatabaseService] ✓ Connected to PostgreSQL")
        except Exception as e:
            self._pool = None
            print(f"[DatabaseService] ✗ PostgreSQL connection failed: {e}")
            raise

    def get_connection(self):
        """
        Get a connection from the pool.
        Caller MUST return it via put_connection() when done.
        """
        self._ensure_connected()
        return self._pool.getconn()

    def put_connection(self, conn):
        """Return a connection to the pool."""
        if self._pool is not None:
            self._pool.putconn(conn)

    def close_all(self):
        """Close all connections in the pool."""
        if self._pool is not None:
            self._pool.closeall()
            print("[DatabaseService] ✓ All connections closed")


# Singleton instance — connection is deferred until first use
db_service = DatabaseService()
