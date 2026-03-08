"""
Database writer – insert / update / delete operations on the coins table.
"""

from typing import Dict, Any, List, Optional
from .service import db_service


class CoinWriter:
    """Handles all write operations to the coins table."""

    def __init__(self, database_service=None):
        self.db = database_service or db_service

    # ------------------------------------------------------------------
    # Single-coin upsert
    # ------------------------------------------------------------------
    def upsert_coin(self, coin: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert a new coin or update it if the id already exists.

        Args:
            coin: Dictionary with keys matching the coins table columns.
                  At minimum: id, symbol, name.

        Returns:
            The upserted row as a dictionary.
        """
        conn = self.db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO coins (
                        id, symbol, name, image_url, github_url,
                        market_cap_rank, circulating_supply, total_supply, max_supply,
                        fully_diluted_valuation,
                        ath, ath_date, atl, atl_date,
                        description, rating_score, rating_notes, review_count, is_featured
                    ) VALUES (
                        %(id)s, %(symbol)s, %(name)s, %(image_url)s, %(github_url)s,
                        %(market_cap_rank)s, %(circulating_supply)s, %(total_supply)s, %(max_supply)s,
                        %(fully_diluted_valuation)s,
                        %(ath)s, %(ath_date)s, %(atl)s, %(atl_date)s,
                        %(description)s, %(rating_score)s, %(rating_notes)s, %(review_count)s, %(is_featured)s
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        symbol                  = EXCLUDED.symbol,
                        name                    = EXCLUDED.name,
                        image_url               = EXCLUDED.image_url,
                        github_url              = COALESCE(EXCLUDED.github_url, coins.github_url),
                        market_cap_rank         = EXCLUDED.market_cap_rank,
                        circulating_supply      = EXCLUDED.circulating_supply,
                        total_supply            = EXCLUDED.total_supply,
                        max_supply              = EXCLUDED.max_supply,
                        fully_diluted_valuation = EXCLUDED.fully_diluted_valuation,
                        ath                     = EXCLUDED.ath,
                        ath_date                = EXCLUDED.ath_date,
                        atl                     = EXCLUDED.atl,
                        atl_date                = EXCLUDED.atl_date,
                        description             = COALESCE(EXCLUDED.description, coins.description),
                        rating_score            = COALESCE(EXCLUDED.rating_score, coins.rating_score),
                        rating_notes            = COALESCE(EXCLUDED.rating_notes, coins.rating_notes),
                        review_count            = COALESCE(EXCLUDED.review_count, coins.review_count),
                        is_featured             = COALESCE(EXCLUDED.is_featured, coins.is_featured)
                    RETURNING *;
                    """,
                    _normalise_coin(coin),
                )
                row = cur.fetchone()
                col_names = [desc[0] for desc in cur.description]
                conn.commit()
                print(f"[CoinWriter] ✓ Upserted coin: {coin.get('id')}")
                return dict(zip(col_names, row))
        except Exception as e:
            conn.rollback()
            print(f"[CoinWriter] ✗ Error upserting coin {coin.get('id')}: {e}")
            raise
        finally:
            self.db.put_connection(conn)

    # ------------------------------------------------------------------
    # Bulk upsert (from CoinGecko /markets response)
    # ------------------------------------------------------------------
    def upsert_coins_from_market_data(self, coins_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Bulk-upsert coins from a CoinGecko /coins/markets response.
        Maps the API fields to the database schema.

        Args:
            coins_list: Raw list of coin dicts from CoinGecko markets endpoint.

        Returns:
            Summary dict with counts.
        """
        success = 0
        failed = 0
        errors: List[str] = []

        for raw in coins_list:
            try:
                mapped = _map_market_data(raw)
                self.upsert_coin(mapped)
                success += 1
            except Exception as e:
                failed += 1
                errors.append(f"{raw.get('id', '?')}: {e}")

        summary = {
            "total": len(coins_list),
            "succeeded": success,
            "failed": failed,
            "errors": errors,
        }
        print(f"[CoinWriter] Bulk upsert complete: {success} ok, {failed} failed")
        return summary

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------
    def delete_coin(self, coin_id: str) -> bool:
        """Delete a coin by ID. Returns True if a row was removed."""
        conn = self.db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM coins WHERE id = %s", (coin_id,))
                deleted = cur.rowcount > 0
                conn.commit()
                if deleted:
                    print(f"[CoinWriter] ✓ Deleted coin: {coin_id}")
                return deleted
        except Exception as e:
            conn.rollback()
            print(f"[CoinWriter] ✗ Error deleting coin {coin_id}: {e}")
            raise
        finally:
            self.db.put_connection(conn)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _normalise_coin(coin: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure all expected keys exist (default to None)."""
    defaults = {
        "id": None,
        "symbol": None,
        "name": None,
        "image_url": None,
        "github_url": None,
        "market_cap_rank": None,
        "circulating_supply": None,
        "total_supply": None,
        "max_supply": None,
        "fully_diluted_valuation": None,
        "ath": None,
        "ath_date": None,
        "atl": None,
        "atl_date": None,
        "description": None,
        "rating_score": None,
        "rating_notes": None,
        "review_count": None,
        "is_featured": None,
    }
    defaults.update(coin)
    return defaults


def _map_market_data(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Map CoinGecko /coins/markets response fields → coins table columns."""
    return {
        "id": raw.get("id"),
        "symbol": raw.get("symbol"),
        "name": raw.get("name"),
        "image_url": raw.get("image"),
        "github_url": None,  # /markets doesn't include github links; use full coin endpoint later if needed
        "market_cap_rank": raw.get("market_cap_rank"),
        "circulating_supply": raw.get("circulating_supply"),
        "total_supply": raw.get("total_supply"),
        "max_supply": raw.get("max_supply"),
        "fully_diluted_valuation": raw.get("fully_diluted_valuation"),
        "ath": raw.get("ath"),
        "ath_date": raw.get("ath_date"),
        "atl": raw.get("atl"),
        "atl_date": raw.get("atl_date"),
        # App-specific fields stay untouched on conflict (COALESCE in SQL)
        "description": None,
        "rating_score": None,
        "rating_notes": None,
        "review_count": None,
        "is_featured": None,
    }


def _map_full_coin_data(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a full CoinGecko /coins/{id} response → coins table columns.
    This endpoint returns much richer data than /markets: description,
    GitHub links, large image, ATH/ATL with dates, etc.
    Used for on-demand DB population when a single coin is looked up.
    """
    market_data = raw.get("market_data") or {}
    links = raw.get("links") or {}
    github_repos = links.get("repos_url", {}).get("github") or []
    # Strip empty strings CoinGecko sometimes returns
    github_repos = [r for r in github_repos if r]

    return {
        "id": raw.get("id"),
        "symbol": raw.get("symbol"),
        "name": raw.get("name"),
        "image_url": (raw.get("image") or {}).get("large"),
        "github_url": github_repos[0] if github_repos else None,
        "market_cap_rank": raw.get("market_cap_rank"),
        "circulating_supply": market_data.get("circulating_supply"),
        "total_supply": market_data.get("total_supply"),
        "max_supply": market_data.get("max_supply"),
        "fully_diluted_valuation": (market_data.get("fully_diluted_valuation") or {}).get("usd"),
        "ath": (market_data.get("ath") or {}).get("usd"),
        "ath_date": (market_data.get("ath_date") or {}).get("usd"),
        "atl": (market_data.get("atl") or {}).get("usd"),
        "atl_date": (market_data.get("atl_date") or {}).get("usd"),
        "description": (raw.get("description") or {}).get("en") or None,
        # App-managed fields – never overwrite existing values
        "rating_score": None,
        "rating_notes": None,
        "review_count": None,
        "is_featured": None,
    }


# Singleton
coin_writer = CoinWriter()
