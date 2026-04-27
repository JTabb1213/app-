"""
Batched Redis writer with pipeline support and multi-exchange aggregation.

Groups incoming NormalizedTick writes into batches and flushes them
to Redis using pipelining for maximum efficiency.

Redis key schema (production):
  rt:coin:<coin_id>                 → consolidated JSON cache entry per coin

Pub/sub channel:
  rt:stream:prices                  → aggregate updates for WebSocket service
"""

import asyncio
import json
import logging
import time
from typing import List, Optional, Set

import redis.asyncio as aioredis

import config
from shared.models import NormalizedTick
from compute.aggregator import PriceAggregator

# Feature flags
ENABLE_DEBUG_KEYS = False       # Write rt:price, rt:ticker keys (verbose)
ENABLE_REDIS_STREAM = False     # Write to rt:ticks append-only log
STREAM_MAXLEN = 10_000

logger = logging.getLogger(__name__)


class RedisWriter:
    """
    Batched async Redis writer with multi-exchange aggregation.

    Production keys (always written):
      rt:avg:<coin_id>      → average price across all active exchanges
      rt:highest:<coin_id>  → exchange with highest price
      rt:lowest:<coin_id>   → exchange with lowest price

    All keys have a short TTL so stale data auto-expires.
    """

    def __init__(self, aggregator: Optional[PriceAggregator] = None):
        self._client: aioredis.Redis = None
        self._buffer: List[NormalizedTick] = []
        self._last_flush: float = time.time()
        self._flush_count: int = 0
        self._write_count: int = 0
        self._aggregator = aggregator or PriceAggregator()

    async def connect(self) -> None:
        if not config.REDIS_URL:
            raise ValueError("REDIS_URL is not set.")
        self._client = aioredis.from_url(config.REDIS_URL, decode_responses=True)
        await self._client.ping()
        logger.info("Connected to Redis")

    async def close(self) -> None:
        if self._buffer:
            await self.flush()
        if self._client:
            await self._client.aclose()
            logger.info("Redis connection closed")

    async def write(self, tick: NormalizedTick) -> None:
        self._buffer.append(tick)
        if len(self._buffer) >= config.BATCH_MAX_SIZE:
            await self.flush()

    async def flush(self) -> None:
        if not self._buffer:
            return

        batch = self._buffer
        self._buffer = []
        _debug_interval_ms = (time.time() - self._last_flush) * 1000
        self._last_flush = time.time()

        updated_coins = self._aggregator.update_batch(batch)

        try:
            pipe = self._client.pipeline(transaction=False)
            ttl = config.RT_PRICE_TTL

            # ── Optional: append-only stream for replay ──
            if ENABLE_REDIS_STREAM:
                for tick in batch:
                    pipe.xadd("rt:ticks", tick.to_dict(), maxlen=STREAM_MAXLEN, approximate=True)

            # ── Optional: debug per-tick keys ──
            if ENABLE_DEBUG_KEYS:
                for tick in batch:
                    tick_data = json.dumps(tick.to_dict())
                    pipe.setex(f"rt:price:{tick.coin_id}", ttl, tick_data)
                    pipe.publish("rt:stream:prices", tick_data)
                    pipe.setex(f"rt:ticker:{tick.exchange}:{tick.coin_id}", ttl, tick_data)

            # ── Production: aggregates (one JSON key per coin) ──
            for coin_id in updated_coins:
                agg = self._aggregator.get_aggregates(coin_id)
                if not agg:
                    continue

                now = agg["timestamp"]
                highest = agg["highest"]
                lowest = agg["lowest"]

                # Single consolidated cache entry per coin
                coin_data = json.dumps({
                    "coin_id": coin_id,
                    "avg_price": agg["avg_price"],
                    "highest": {
                        "exchange": highest.exchange,
                        "price": highest.price,
                        "bid": highest.bid,
                        "ask": highest.ask,
                        "timestamp": highest.timestamp,
                    },
                    "lowest": {
                        "exchange": lowest.exchange,
                        "price": lowest.price,
                        "bid": lowest.bid,
                        "ask": lowest.ask,
                        "timestamp": lowest.timestamp,
                    },
                    "exchange_count": agg["exchange_count"],
                    "exchanges": sorted(agg["exchanges"].keys()),
                    "timestamp": now,
                })
                pipe.setex(f"rt:coin:{coin_id}", ttl, coin_data)

                # Publish aggregate to WS service
                agg_msg = json.dumps({
                    "type": "aggregate",
                    "coin_id": coin_id,
                    "avg_price": agg["avg_price"],
                    "highest_exchange": highest.exchange,
                    "highest_price": highest.price,
                    "lowest_exchange": lowest.exchange,
                    "lowest_price": lowest.price,
                    "exchange_count": agg["exchange_count"],
                    "timestamp": now,
                    "published_at": int(time.time() * 1000),
                })
                pipe.publish("rt:stream:prices", agg_msg)

            await pipe.execute()

            self._flush_count += 1
            self._write_count += len(batch)

            if self._flush_count % 20 == 0:
                logger.info(
                    f"Flush #{self._flush_count}: {len(batch)} ticks, "
                    f"{len(updated_coins)} coins, "
                    f"interval: {_debug_interval_ms:.0f}ms"
                )

        except Exception as e:
            logger.error(f"Redis pipeline flush failed: {e}")
            self._buffer = batch + self._buffer

    async def flush_loop(self) -> None:
        interval = config.BATCH_INTERVAL_MS / 1000.0
        logger.info(
            f"Flush loop started (interval: {config.BATCH_INTERVAL_MS}ms, "
            f"max batch: {config.BATCH_MAX_SIZE})"
        )
        while True:
            await asyncio.sleep(interval)
            await self.flush()

    @property
    def stats(self) -> dict:
        return {
            "flush_count": self._flush_count,
            "total_writes": self._write_count,
            "buffer_size": len(self._buffer),
        }
