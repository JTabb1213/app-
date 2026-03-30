"""
Batched Redis writer with pipeline support and multi-exchange aggregation.

Groups incoming NormalizedTick writes into batches and flushes them
to Redis using pipelining for maximum efficiency.

Architecture:
    Ticks → Buffer → Aggregator (compute) → Redis Pipeline (write)

The aggregator is injected, keeping this class focused on I/O only.

Redis key schema (production):
  rt:avg:<coin_id>                  → average price across all exchanges
  rt:best:<coin_id>                 → exchange with highest price
  rt:worst:<coin_id>                → exchange with lowest price

Redis key schema (debug, can be disabled):
  rt:price:<coin_id>                → latest price (from any exchange)
  rt:ticker:<exchange>:<coin_id>    → per-exchange ticker data

Redis Stream (optional, for replay/recovery):
  rt:ticks                          → append-only log of all normalized ticks
"""

import asyncio
import json
import logging
import time
from typing import List, Optional, Set

import redis.asyncio as aioredis

import config
from core.models import NormalizedTick
from compute.aggregator import PriceAggregator

# =============================================================================
# FEATURE FLAGS — toggle optional behaviors without code changes
# =============================================================================
ENABLE_DEBUG_KEYS = True      # Write rt:price, rt:ticker keys (verbose, for debugging)
ENABLE_REDIS_STREAM = False   # Write to rt:ticks Stream (for replay/recovery)
STREAM_MAXLEN = 10_000        # Cap stream length (~10K entries, auto-trimmed)
# =============================================================================

logger = logging.getLogger(__name__)


class RedisWriter:
    """
    Batched async Redis writer with multi-exchange aggregation.

    Production keys (always written):
      rt:avg:<coin_id>                → average price across all active exchanges
      rt:best:<coin_id>               → exchange with highest price
      rt:worst:<coin_id>              → exchange with lowest price

    Debug keys (controlled by ENABLE_DEBUG_KEYS):
      rt:price:<coin_id>              → latest price data (from last exchange)
      rt:ticker:<exchange>:<coin_id>  → per-exchange ticker data

    All keys have a short TTL (default 300s) so stale data auto-expires.
    """

    def __init__(self, aggregator: Optional[PriceAggregator] = None):
        self._client: aioredis.Redis = None
        self._buffer: List[NormalizedTick] = []
        self._last_flush: float = time.time()
        self._flush_count: int = 0
        self._write_count: int = 0
        
        # Aggregator handles all computation (injected for testability)
        self._aggregator = aggregator or PriceAggregator()

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

        _debug_interval_ms = (time.time() - self._last_flush) * 1000
        self._last_flush = time.time()

        # Update aggregator with all ticks in this batch
        updated_coins = self._aggregator.update_batch(batch)

        try:
            pipe = self._client.pipeline(transaction=False)
            ttl = config.RT_PRICE_TTL
            _debug_total_bytes = 0
            _RESP_OVERHEAD = 30

            # ==================================================================
            # OPTIONAL: Write to Redis Stream for replay/recovery
            # ==================================================================
            if ENABLE_REDIS_STREAM:
                for tick in batch:
                    tick_data = tick.to_dict()
                    # XADD rt:ticks MAXLEN ~10000 * field1 val1 field2 val2 ...
                    pipe.xadd(
                        "rt:ticks",
                        tick_data,
                        maxlen=STREAM_MAXLEN,
                        approximate=True,
                    )

            # ==================================================================
            # DEBUG KEYS: Per-tick and per-exchange data (disable in prod)
            # ==================================================================
            if ENABLE_DEBUG_KEYS:
                for tick in batch:
                    tick_data = json.dumps(tick.to_dict())

                    # rt:price:<coin_id> — latest from any exchange
                    price_key = f"rt:price:{tick.coin_id}"
                    pipe.setex(price_key, ttl, tick_data)

                    # Publish raw tick to WS stream
                    pipe.publish("rt:stream:prices", tick_data)

                    # rt:ticker:<exchange>:<coin_id> — per-exchange
                    exchange_key = f"rt:ticker:{tick.exchange}:{tick.coin_id}"
                    pipe.setex(exchange_key, ttl, tick_data)

                    _debug_total_bytes += (
                        len(price_key.encode()) + len(tick_data.encode()) + _RESP_OVERHEAD
                        + len(exchange_key.encode()) + len(tick_data.encode()) + _RESP_OVERHEAD
                    )

            # ==================================================================
            # PRODUCTION KEYS: Aggregates (avg, best, worst) — always written
            # ==================================================================
            for coin_id in updated_coins:
                agg = self._aggregator.get_aggregates(coin_id)
                if not agg:
                    continue
                
                now = agg["timestamp"]
                best = agg["best"]
                worst = agg["worst"]
                
                # rt:avg:<coin_id> — average price across exchanges
                avg_data = json.dumps({
                    "coin_id": coin_id,
                    "avg_price": agg["avg_price"],
                    "exchange_count": agg["exchange_count"],
                    "timestamp": now,
                })
                avg_key = f"rt:avg:{coin_id}"
                pipe.setex(avg_key, ttl, avg_data)
                
                # rt:best:<coin_id> — highest priced exchange
                best_data = json.dumps({
                    "coin_id": coin_id,
                    "exchange": best.exchange,
                    "price": best.price,
                    "bid": best.bid,
                    "ask": best.ask,
                    "timestamp": best.timestamp,
                })
                best_key = f"rt:best:{coin_id}"
                pipe.setex(best_key, ttl, best_data)
                
                # rt:worst:<coin_id> — lowest priced exchange
                worst_data = json.dumps({
                    "coin_id": coin_id,
                    "exchange": worst.exchange,
                    "price": worst.price,
                    "bid": worst.bid,
                    "ask": worst.ask,
                    "timestamp": worst.timestamp,
                })
                worst_key = f"rt:worst:{coin_id}"
                pipe.setex(worst_key, ttl, worst_data)
                
                # Publish aggregate to WS stream
                agg_msg = json.dumps({
                    "type": "aggregate",
                    "coin_id": coin_id,
                    "avg_price": agg["avg_price"],
                    "best_exchange": best.exchange,
                    "best_price": best.price,
                    "worst_exchange": worst.exchange,
                    "worst_price": worst.price,
                    "exchange_count": agg["exchange_count"],
                    "timestamp": now,
                })
                pipe.publish("rt:stream:prices", agg_msg)
                
                _debug_total_bytes += (
                    len(avg_key.encode()) + len(avg_data.encode()) + _RESP_OVERHEAD
                    + len(best_key.encode()) + len(best_data.encode()) + _RESP_OVERHEAD
                    + len(worst_key.encode()) + len(worst_data.encode()) + _RESP_OVERHEAD
                )

            await pipe.execute()

            self._flush_count += 1
            self._write_count += len(batch)

            # Log every 20th flush
            if self._flush_count % 20 == 0:
                logger.info(
                    f"Flush #{self._flush_count}: {len(batch)} ticks, "
                    f"{len(updated_coins)} coins, "
                    f"~{_debug_total_bytes / 1024:.1f} KB, "
                    f"interval: {_debug_interval_ms:.0f}ms"
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
