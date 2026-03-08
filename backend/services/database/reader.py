"""
Database reader – read-only queries on the coins table.
"""

from typing import Dict, Any, List, Optional
from .service import db_service


class CoinReader:
    """Handles all read operations on the coins table."""

    def __init__(self, database_service=None):
        self.db = database_service or db_service

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _row_to_dict(row, description) -> Dict[str, Any]:
        """Convert a psycopg2 row + cursor.description to a dict."""
        col_names = [desc[0] for desc in description]
        d = dict(zip(col_names, row))
        # Convert datetimes to ISO strings for JSON serialisation
        for key in ("ath_date", "atl_date", "created_at", "updated_at"):
            if key in d and d[key] is not None:
                d[key] = d[key].isoformat()
        # Convert Decimal → float for JSON serialisation
        from decimal import Decimal
        for k, v in d.items():
            if isinstance(v, Decimal):
                d[k] = float(v)
        return d

    # ------------------------------------------------------------------
    # Single coin
    # ------------------------------------------------------------------
    def get_coin(self, coin_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single coin by its ID.

        Args:
            coin_id: The coin identifier (e.g. "bitcoin")

        Returns:
            Coin dict or None if not found.
        """
        conn = self.db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM coins WHERE id = %s", (coin_id.lower(),))
                row = cur.fetchone()
                if row:
                    return self._row_to_dict(row, cur.description)
                return None
        except Exception as e:
            print(f"[CoinReader] ✗ Error reading coin {coin_id}: {e}")
            raise
        finally:
            self.db.put_connection(conn)

    # ------------------------------------------------------------------
    # Multiple coins by rank
    # ------------------------------------------------------------------
    def get_top_coins(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve the top coins ordered by market_cap_rank.

        Args:
            limit: How many coins to return (default 50)

        Returns:
            List of coin dicts.
        """
        conn = self.db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM coins ORDER BY market_cap_rank ASC NULLS LAST LIMIT %s",
                    (limit,),
                )
                rows = cur.fetchall()
                return [self._row_to_dict(r, cur.description) for r in rows]
        except Exception as e:
            print(f"[CoinReader] ✗ Error reading top coins: {e}")
            raise
        finally:
            self.db.put_connection(conn)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def search_coins(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search coins by id, symbol, or name (case-insensitive ILIKE).

        Args:
            query: Search term
            limit: Max results

        Returns:
            List of matching coin dicts.
        """
        conn = self.db.get_connection()
        try:
            pattern = f"%{query}%"
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM coins
                    WHERE id ILIKE %s OR symbol ILIKE %s OR name ILIKE %s
                    ORDER BY market_cap_rank ASC NULLS LAST
                    LIMIT %s
                    """,
                    (pattern, pattern, pattern, limit),
                )
                rows = cur.fetchall()
                return [self._row_to_dict(r, cur.description) for r in rows]
        except Exception as e:
            print(f"[CoinReader] ✗ Error searching coins: {e}")
            raise
        finally:
            self.db.put_connection(conn)

    # ------------------------------------------------------------------
    # All coins (paginated)
    # ------------------------------------------------------------------
    def get_all_coins(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """
        Return a paginated list of all coins.

        Returns:
            Dict with 'coins', 'page', 'per_page', 'total'.
        """
        conn = self.db.get_connection()
        try:
            offset = (page - 1) * per_page
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM coins")
                total = cur.fetchone()[0]

                cur.execute(
                    "SELECT * FROM coins ORDER BY market_cap_rank ASC NULLS LAST LIMIT %s OFFSET %s",
                    (per_page, offset),
                )
                rows = cur.fetchall()
                coins = [self._row_to_dict(r, cur.description) for r in rows]

            return {
                "coins": coins,
                "page": page,
                "per_page": per_page,
                "total": total,
            }
        except Exception as e:
            print(f"[CoinReader] ✗ Error reading all coins: {e}")
            raise
        finally:
            self.db.put_connection(conn)


# Singleton
coin_reader = CoinReader()
