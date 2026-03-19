"""
Batched Redis writer with pipeline support.

Groups incoming NormalizedTick writes into batches and flushes them
to Redis using pipelining for maximum efficiency.

Batching strategy (time-or-count, whichever comes first):
  - Flush when BATCH_MAX_SIZE ticks have accumulated, OR
  - Flush when BATCH_INTERVAL_MS has elapsed since the last flush

Without batching:  ~200 Redis calls/sec (one per tick)
With batching:     ~2 pipeline calls/sec containing ~100 ops each
  → 100× fewer network round-trips
  → Tradeoff: up to 500ms staleness (configurable, acceptable for display)

Redis key schema:
  rt:price:<coin_id>                → latest price (from any exchange)
  rt:ticker:<exchange>:<coin_id>    → per-exchange ticker data

The rt: prefix separates realtime data (sub-second writes, short TTL)
from the existing crypto:tokenomics: cache (10-min TTL, from CoinGecko).
Both coexist in the same Redis instance cleanly.
"""

import asyncio
import json
import logging
import time
from typing import List

import redis.asyncio as aioredis

import config
from core.models import NormalizedTick

logger = logging.getLogger(__name__)


class RedisWriter:
    """
    Batched async Redis writer.

    Two keys are written per tick:
      rt:price:<coin_id>              → latest aggregated price data
      rt:ticker:<exchange>:<coin_id>  → per-exchange ticker data

    Both have a short TTL (default 30s) so stale data auto-expires
    if this service goes down.  The service writes far more frequently
    than the TTL, so keys stay alive continuously during normal operation.
    """

    def __init__(self):
        self._client: aioredis.Redis = None
        self._buffer: List[NormalizedTick] = []
        self._last_flush: float = time.time()
        self._flush_count: int = 0
        self._write_count: int = 0

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Initialize the async Redis connection."""
        if not config.REDIS_URL:
            raise ValueError(
                "REDIS_URL is not set. "
                "Copy .env.example to .env and add your Redis URL."
            )

        self._client = aioredis.from_url(
            config.REDIS_URL,
            decode_responses=True,
        )

        # Verify connection
        await self._client.ping()
        logger.info("Connected to Redis")

    async def close(self) -> None:
        """Close the Redis connection gracefully."""
        # Flush any remaining buffered ticks before closing
        if self._buffer:
            await self.flush()
        if self._client:
            await self._client.aclose()
            logger.info("Redis connection closed")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def write(self, tick: NormalizedTick) -> None:
        """
        Add a normalized tick to the write buffer.
        Triggers an immediate flush if the buffer reaches BATCH_MAX_SIZE.
        """
        self._buffer.append(tick)

        if len(self._buffer) >= config.BATCH_MAX_SIZE:
            await self.flush()

    async def flush(self) -> None:
        """
        Flush all buffered ticks to Redis in a single pipeline.

        Called automatically by:
          - write()      when buffer is full (size-triggered)
          - flush_loop() when interval elapses (time-triggered)
        """
        if not self._buffer:
            return

        # Swap out the buffer so new writes don't interfere with the flush
        batch = self._buffer
        self._buffer = []
        self._last_flush = time.time()

        try:
            pipe = self._client.pipeline(transaction=False)
            ttl = config.RT_PRICE_TTL

            for tick in batch:
                tick_data = json.dumps(tick.to_dict())

                # Key 1: Latest price for this coin (from any exchange)
                # This is what the API layer reads for
                # "what is bitcoin's price right now?"
                price_key = f"rt:price:{tick.coin_id}"
                pipe.setex(price_key, ttl, tick_data)

                # Key 2: Per-exchange ticker data
                # Useful for cross-exchange comparison, spread analysis,
                # and debugging which exchange is providing data
                exchange_key = f"rt:ticker:{tick.exchange}:{tick.coin_id}"
                pipe.setex(exchange_key, ttl, tick_data)

            await pipe.execute()

            self._flush_count += 1
            self._write_count += len(batch)

            # Log every 20th flush to avoid spam
            if self._flush_count % 20 == 0:
                logger.info(
                    f"Flush #{self._flush_count}: {len(batch)} ticks "
                    f"({self._write_count} total writes)"
                )

        except Exception as e:
            logger.error(f"Redis pipeline flush failed: {e}")
            # Put ticks back in the buffer so they aren't lost
            self._buffer = batch + self._buffer

    # ------------------------------------------------------------------
    # Flush loop (runs as a background asyncio task)
    # ------------------------------------------------------------------

    async def flush_loop(self) -> None:
        """
        Periodically flush the buffer to Redis.

        Ensures data is written even during low-traffic periods
        when the buffer doesn't fill up on its own.  Without this,
        a single tick could sit in the buffer indefinitely until
        99 more arrive.
        """
        interval = config.BATCH_INTERVAL_MS / 1000.0    # ms → seconds

        logger.info(
            f"Flush loop started "
            f"(interval: {config.BATCH_INTERVAL_MS}ms, "
            f"max batch: {config.BATCH_MAX_SIZE})"
        )

        while True:
            await asyncio.sleep(interval)
            await self.flush()

    # ------------------------------------------------------------------
    # Stats for health check endpoint
    # ------------------------------------------------------------------

    @property
    def stats(self) -> dict:
        return {
            "flush_count": self._flush_count,
            "total_writes": self._write_count,
            "buffer_size": len(self._buffer),
        }
