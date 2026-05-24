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
        deduplicate: bool = True,
        aggregate_volume: bool = False,
    ):
        self._client = redis_client
        self._stream_key = stream_key
        self._batch_size = batch_size
        self._flush_interval = flush_interval_ms / 1000.0
        self._max_stream_len = max_stream_len
        self._deduplicate = deduplicate
        self._aggregate_volume = aggregate_volume

        # deduplicate=True  → dict[(exchange, pair) → RawTick]  (latest tick wins)
        # aggregate_volume=True → dict[(exchange, pair) → {buy_vol, sell_vol, count}]
        # both False         → plain list (raw, no dedup)
        if aggregate_volume:
            self._buffer: dict | List[RawTick] = {}
        elif deduplicate:
            self._buffer = {}
        else:
            self._buffer = []
        self._lock = asyncio.Lock()

        # Stats
        self._produced = 0
        self._dropped = 0   # ticks overwritten by a newer one in same window
        self._flushed = 0
        self._flush_count = 0
        self._errors = 0

    async def put(self, tick: RawTick) -> None:
        """Add a tick to the in-memory buffer (instant, no I/O)."""
        self._produced += 1

        if self._aggregate_volume:
            # Accumulate buy/sell volume per (exchange, pair).
            # Expects tick.data to have: price (float), size (float), side (str)
            key = (tick.exchange, tick.pair)
            try:
                size_val = float(tick.data.get("size", 0) or tick.data.get("qty", 0))
                side = tick.data.get("side", "buy").lower()
            except (ValueError, TypeError):
                return
            if size_val <= 0:
                return
            if key not in self._buffer:
                self._buffer[key] = {
                    "buy_vol": 0.0, "sell_vol": 0.0,
                    "trade_count": 0, "exchange": tick.exchange,
                    "pair": tick.pair, "received_at": tick.received_at,
                }
            else:
                self._dropped += 1  # consolidated, not truly dropped
            if side == "buy":
                self._buffer[key]["buy_vol"] += size_val
            else:
                self._buffer[key]["sell_vol"] += size_val
            self._buffer[key]["trade_count"] += 1
            self._buffer[key]["received_at"] = tick.received_at  # keep latest ts
            buf_size = len(self._buffer)
        elif self._deduplicate:
            key = (tick.exchange, tick.pair)
            if key in self._buffer:
                self._dropped += 1
            self._buffer[key] = tick
            buf_size = len(self._buffer)
        else:
            self._buffer.append(tick)
            buf_size = len(self._buffer)

        if buf_size >= self._batch_size:
            await self.flush()

    async def flush(self) -> None:
        """Batch-write all buffered ticks to the Redis Stream."""
        if not self._buffer:
            return

        async with self._lock:
            if self._aggregate_volume:
                # Serialize accumulated buckets as flat dicts for XADD
                raw_batch = list(self._buffer.values())
                self._buffer = {}
                batch = raw_batch   # list of plain dicts, not RawTick
            elif self._deduplicate:
                batch = list(self._buffer.values())
                self._buffer = {}
            else:
                batch = self._buffer
                self._buffer = []

        try:
            pipe = self._client.pipeline(transaction=False)

            for tick in batch:
                if self._aggregate_volume:
                    entry = self._serialize_aggregate(tick)
                else:
                    entry = self._serialize(tick)
                pipe.xadd(
                    self._stream_key,
                    entry,
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
                if self._aggregate_volume:
                    # Merge failed buckets back; current buffer wins (already has newer data)
                    recovered = {(b["exchange"], b["pair"]): b for b in batch}
                    recovered.update(self._buffer)
                    self._buffer = recovered
                elif self._deduplicate:
                    recovered = {(t.exchange, t.pair): t for t in batch}
                    recovered.update(self._buffer)
                    self._buffer = recovered
                else:
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

    @staticmethod
    def _serialize_aggregate(bucket: dict) -> dict:
        """Serialize a pre-aggregated volume bucket to a flat {str: str} dict.

        Packs aggregate fields into 'data' as JSON so the existing StreamConsumer
        _deserialize() method (which does json.loads(fields['data'])) works unchanged.
        """
        return {
            "exchange":    bucket["exchange"],
            "pair":        bucket["pair"],
            "received_at": str(bucket["received_at"]),
            "data": json.dumps({
                "buy_vol":      bucket["buy_vol"],
                "sell_vol":     bucket["sell_vol"],
                "trade_count":  bucket["trade_count"],
                "is_aggregated": "1",
            }),
        }

    @property
    def stats(self) -> dict:
        return {
            "produced": self._produced,
            "dropped_as_duplicate": self._dropped,
            "flushed_to_stream": self._flushed,
            "flush_count": self._flush_count,
            "dedup_ratio_pct": (
                round(self._dropped / self._produced * 100, 1)
                if self._produced else 0
            ),
            "buffer_size": len(self._buffer),
            "errors": self._errors,
        }
