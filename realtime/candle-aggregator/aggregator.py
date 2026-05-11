"""
Core aggregation logic for the candle-aggregator service.

CandleAggregator reads from a lower-resolution candle table and upserts
rolled-up candles into a higher-resolution destination table.

Roll-up logic:
  - open  = FIRST open in the window (ordered by bucket asc)
  - high  = MAX of all highs in the window
  - low   = MIN of all lows in the window
  - close = LAST close in the window (ordered by bucket desc)
  - volume = SUM of all volumes in the window

All upserts use ON CONFLICT DO UPDATE so re-runs are fully idempotent.
The service can crash and restart at any time without losing or corrupting data.
"""

import logging
import time
from typing import Optional

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)


# Map resolution string → SQL truncation interval for date_trunc()
# PostgreSQL's date_trunc understands: 'hour', 'day', 'week', 'month'
RESOLUTION_TRUNC = {
    "1h":     "hour",
    "1d":     "day",
    "1w":     "week",
    "1month": "month",
}


class CandleAggregator:
    """
    Connects to Postgres and rolls up candle data between tables.

    Each call to aggregate() is self-contained:
      1. Opens a connection (or reuses existing healthy one)
      2. Runs a single SQL INSERT … SELECT … ON CONFLICT DO UPDATE
      3. Commits and logs results

    No state is held between runs — everything is computed from the DB.
    """

    def __init__(self, db_url: str) -> None:
        self._db_url = db_url
        self._conn: Optional[psycopg2.extensions.connection] = None

    # ── Connection management ─────────────────────────────────────────────────

    def _get_conn(self) -> psycopg2.extensions.connection:
        """Return a live DB connection, reconnecting if needed."""
        try:
            if self._conn is None or self._conn.closed:
                raise psycopg2.OperationalError("no connection")
            # Quick liveness check
            self._conn.cursor().execute("SELECT 1")
        except Exception:
            logger.info("Connecting to Postgres…")
            primary = self._db_url
            try:
                self._conn = psycopg2.connect(primary)
            except psycopg2.OperationalError as e:
                import config as _cfg
                fallback = _cfg.DATABASE_URL_IPV4 if hasattr(_cfg, "DATABASE_URL_IPV4") else None
                if fallback and fallback != primary:
                    logger.warning(f"Primary DB failed ({e}), trying IPv4 fallback…")
                    self._conn = psycopg2.connect(fallback)
                else:
                    raise
            logger.info("Connected to Postgres")
        return self._conn

    # ── Main aggregation ──────────────────────────────────────────────────────

    def aggregate(
        self,
        source_table: str,
        dest_table: str,
        dest_resolution: str,
        source_window_hours: Optional[int] = None,
    ) -> None:
        """
        Roll up `source_table` candles into `dest_table`.

        Parameters
        ----------
        source_table        e.g. "price_candles_1h"
        dest_table          e.g. "price_candles_1d"
        dest_resolution     e.g. "1d"  — must be a key in RESOLUTION_TRUNC
        source_window_hours Optional. If set, only process rows from the last
                            N hours (useful for partial runs). If None, process
                            all rows (full history rebuild).
        """
        trunc = RESOLUTION_TRUNC.get(dest_resolution)
        if trunc is None:
            logger.error(
                f"Unknown resolution '{dest_resolution}'. "
                f"Valid: {list(RESOLUTION_TRUNC.keys())}"
            )
            return

        logger.info(
            f"[{source_table} → {dest_table}] "
            f"resolution={dest_resolution} trunc={trunc}"
        )

        # Build optional time filter
        if source_window_hours:
            time_filter = (
                f"AND bucket >= NOW() - INTERVAL '{source_window_hours} hours'"
            )
        else:
            time_filter = ""

        # This single SQL statement does the entire job:
        #
        #   1. Groups all source rows by (coin_id, date_trunc(bucket))
        #   2. Computes OHLCV for each group
        #   3. Upserts into the destination table
        #   4. On conflict (same coin + same bucket already exists), updates
        #      the row — this handles in-progress candles that get re-computed
        sql = f"""
            INSERT INTO {dest_table}
                (coin_id, bucket, open, high, low, close, volume, exchange_count, tick_count)

            SELECT
                coin_id,

                -- Round bucket down to the destination resolution boundary
                date_trunc('{trunc}', bucket AT TIME ZONE 'UTC') AT TIME ZONE 'UTC'
                    AS bucket,

                -- OPEN  = the open price of the FIRST source candle in the window
                (array_agg(open  ORDER BY bucket ASC))[1]  AS open,

                -- HIGH  = the maximum high across all source candles
                MAX(high)                                   AS high,

                -- LOW   = the minimum low across all source candles
                MIN(low)                                    AS low,

                -- CLOSE = the close price of the LAST source candle in the window
                (array_agg(close ORDER BY bucket DESC))[1] AS close,

                -- VOLUME = sum of all source candle volumes
                SUM(volume)                                 AS volume,

                -- EXCHANGE_COUNT = max seen (best approximation for rolled-up bars)
                MAX(exchange_count)                         AS exchange_count,

                -- TICK_COUNT = total ticks aggregated
                SUM(tick_count)                             AS tick_count

            FROM {source_table}
            WHERE 1=1 {time_filter}

            GROUP BY
                coin_id,
                date_trunc('{trunc}', bucket AT TIME ZONE 'UTC')

            ON CONFLICT (coin_id, bucket)
            DO UPDATE SET
                open           = EXCLUDED.open,
                high           = EXCLUDED.high,
                low            = EXCLUDED.low,
                close          = EXCLUDED.close,
                volume         = EXCLUDED.volume,
                exchange_count = EXCLUDED.exchange_count,
                tick_count     = EXCLUDED.tick_count
        """

        t0 = time.time()
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(sql)
                rows_affected = cur.rowcount
            conn.commit()
            elapsed = time.time() - t0
            logger.info(
                f"[{source_table} → {dest_table}] "
                f"upserted {rows_affected} rows in {elapsed:.2f}s"
            )
        except Exception as e:
            logger.error(
                f"[{source_table} → {dest_table}] aggregation failed: {e}"
            )
            # Reset connection so next run gets a fresh one
            try:
                self._conn.rollback()
            except Exception:
                self._conn = None
