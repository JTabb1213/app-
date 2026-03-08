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
    All database operations should acquire connections through this service.
    """

    def __init__(self, database_url: str = DATABASE_URL, min_conn: int = 1, max_conn: int = 10):
        """
        Initialize the connection pool.

        Args:
            database_url: PostgreSQL connection string
            min_conn: Minimum connections in the pool
            max_conn: Maximum connections in the pool
        """
        self.database_url = database_url
        self._pool: Optional[pool.SimpleConnectionPool] = None
        self._connect(min_conn, max_conn)

    def _connect(self, min_conn: int, max_conn: int):
        """Create the connection pool."""
        try:
            self._pool = pool.SimpleConnectionPool(
                min_conn,
                max_conn,
                self.database_url
            )
            # Quick connectivity check
            conn = self._pool.getconn()
            conn.cursor().execute("SELECT 1")
            self._pool.putconn(conn)
            print("[DatabaseService] ✓ Connected to PostgreSQL")
        except Exception as e:
            print(f"[DatabaseService] ✗ PostgreSQL connection failed: {e}")
            raise

    def get_connection(self):
        """
        Get a connection from the pool.
        Caller MUST return it via put_connection() when done.
        """
        if self._pool is None:
            raise RuntimeError("Database pool not initialised")
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


# Singleton instance
db_service = DatabaseService()
