"""
Redis Stream producer with in-memory batching.

Exchange connectors push raw ticks here.  The producer buffers them
in memory and periodically flushes the batch to a Redis Stream
using pipelined XADD commands.

Why batch instead of one-by-one?
  - Websockets can produce thousands of ticks/second
  - Individual XADD calls would saturate the Redis round-trip budget
  - Pipelined batch writes are 10–50× more efficient
  - The in-memory buffer absorbs bursts without back-pressure on the WS

Flow:
    connector._emit(tick)  →  producer.put(tick)   [instant, in-memory]
                                    ↓
                             in-memory buffer
                                    ↓   (flush on size OR timer)
                             Redis XADD pipeline   [batched network I/O]
"""

import asyncio
import json
import logging
import time
from typing import List

import redis.asyncio as aioredis

from shared.models import RawTick

logger = logging.getLogger(__name__)


class StreamProducer:
    """
    Buffers RawTick events in memory and flushes them to a Redis Stream
    in efficient batches.

    Two flush triggers:
      1. Size:  buffer reaches ``batch_size`` → immediate flush
      2. Timer: ``flush_interval_ms`` elapses  → periodic flush
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        stream_key: str,
        batch_size: int = 50,
        flush_interval_ms: int = 500,
        max_stream_len: int = 50_000,
    ):
        self._client = redis_client
        self._stream_key = stream_key
        self._batch_size = batch_size
        self._flush_interval = flush_interval_ms / 1000.0
        self._max_stream_len = max_stream_len

        self._buffer: List[RawTick] = []
        self._lock = asyncio.Lock()

        # Stats
        self._produced = 0
        self._flushed = 0
        self._flush_count = 0
        self._errors = 0

    async def put(self, tick: RawTick) -> None:
        """Add a tick to the in-memory buffer (instant, no I/O)."""
        self._buffer.append(tick)
        self._produced += 1

        if len(self._buffer) >= self._batch_size:
            await self.flush()

    async def flush(self) -> None:
        """Batch-write all buffered ticks to the Redis Stream."""
        if not self._buffer:
            return

        async with self._lock:
            batch = self._buffer
            self._buffer = []

        try:
            pipe = self._client.pipeline(transaction=False)

            for tick in batch:
                pipe.xadd(
                    self._stream_key,
                    self._serialize(tick),
                    maxlen=self._max_stream_len,
                    approximate=True,
                )

            await pipe.execute()

            self._flushed += len(batch)
            self._flush_count += 1

            if self._flush_count % 50 == 0:
                logger.info(
                    f"[stream-producer] Flush #{self._flush_count}: "
                    f"{len(batch)} ticks → {self._stream_key} "
                    f"(total: {self._flushed})"
                )

        except Exception as e:
            self._errors += 1
            logger.error(f"[stream-producer] Flush failed: {e}")
            async with self._lock:
                self._buffer = batch + self._buffer

    async def flush_loop(self) -> None:
        """Periodic flush — bounds max latency to flush_interval."""
        logger.info(
            f"[stream-producer] Flush loop started "
            f"(interval: {self._flush_interval * 1000:.0f}ms, "
            f"batch_size: {self._batch_size}, "
            f"stream: {self._stream_key}, "
            f"maxlen: ~{self._max_stream_len})"
        )

        while True:
            await asyncio.sleep(self._flush_interval)
            await self.flush()

    @staticmethod
    def _serialize(tick: RawTick) -> dict:
        """Serialize a RawTick to flat {str: str} dict for Redis Stream."""
        return {
            "exchange": tick.exchange,
            "pair": tick.pair,
            "data": json.dumps(tick.data),
            "received_at": str(tick.received_at),
        }

    @property
    def stats(self) -> dict:
        return {
            "produced": self._produced,
            "flushed_to_stream": self._flushed,
            "flush_count": self._flush_count,
            "buffer_size": len(self._buffer),
            "errors": self._errors,
        }
