"""
Pipeline orchestrator — wires together the exchange connectors,
ingestion queue, normalizer, and Redis writer.

Architecture:

    Exchange Connectors  →  Ingestion Queue  →  Normalizer  →  Redis Writer
         (async ws)         (asyncio.Queue)       (sync)       (batched async)

    ┌───────────────┐     ┌────────────────┐     ┌────────────┐     ┌──────────┐
    │    Kraken WS   │────▶│ Ingestion Queue │────▶│ Normalizer │────▶│  Redis   │
    │   (producer)   │     │  (max 10,000)  │     │  (worker)  │     │ (writer) │
    └───────────────┘     └────────────────┘     └────────────┘     └──────────┘
           │                                            │                 │
     never blocks                                alias lookup      batch flush
     (queue absorbs                              + field mapping    every 500ms
      bursts)                                                      or 100 ticks

The queue decouples the websocket receive loop from processing,
ensuring the connector never blocks on normalization or Redis writes.
"""

import asyncio
import logging
import time
from typing import List

from core.models import RawTick
from exchanges.base import BaseExchange
from normalizer.normalizer import Normalizer
from storage.redis_writer import RedisWriter

logger = logging.getLogger(__name__)


class Pipeline:
    """
    Orchestrates the full realtime data pipeline.

    Components:
      - Exchange connectors: produce RawTick events
      - Ingestion queue: decouples receiving from processing
      - Normalizer: converts RawTick → NormalizedTick
      - Redis writer: batched pipeline writes to Redis

    All components run as concurrent asyncio tasks.
    """

    def __init__(
        self,
        connectors: List[BaseExchange],
        normalizer: Normalizer,
        writer: RedisWriter,
        queue: asyncio.Queue,
    ):
        self.connectors = connectors
        self.normalizer = normalizer
        self.writer = writer
        self.queue = queue

        # Stats
        self._raw_count = 0
        self._normalized_count = 0
        self._dropped_count = 0
        self._start_time: float = 0

    # ------------------------------------------------------------------
    # Run the full pipeline
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """
        Start all pipeline components as concurrent tasks.
        Runs forever until cancelled or a critical task crashes.
        """
        self._start_time = time.time()
        logger.info("Pipeline starting...")

        tasks = []

        # 1. Exchange connectors (producers → ingestion queue)
        for connector in self.connectors:
            tasks.append(asyncio.create_task(
                connector.run(),
                name=f"connector:{connector.NAME}",
            ))

        # 2. Worker (ingestion queue → normalizer → Redis writer)
        tasks.append(asyncio.create_task(
            self._process_loop(),
            name="worker",
        ))

        # 3. Redis flush loop (periodic batch writes)
        tasks.append(asyncio.create_task(
            self.writer.flush_loop(),
            name="redis-flusher",
        ))

        # 4. Stats logger (periodic health output)
        tasks.append(asyncio.create_task(
            self._stats_loop(),
            name="stats",
        ))

        logger.info(
            f"Pipeline running with {len(self.connectors)} connector(s): "
            f"{[c.NAME for c in self.connectors]}"
        )

        # Wait for all tasks — they run forever.  If one crashes,
        # log the error and cancel the rest.
        done, pending = await asyncio.wait(
            tasks, return_when=asyncio.FIRST_EXCEPTION
        )

        for task in done:
            if task.exception():
                logger.error(
                    f"Task '{task.get_name()}' crashed: {task.exception()}"
                )

        for task in pending:
            task.cancel()

    # ------------------------------------------------------------------
    # Worker loop
    # ------------------------------------------------------------------

    async def _process_loop(self) -> None:
        """
        Worker loop: pulls RawTick from the ingestion queue,
        normalizes them, and sends NormalizedTick to the Redis writer.

        This is the core of the pipeline — the single point where
        raw exchange data becomes canonical data.
        """
        logger.info("Worker started — processing ingestion queue")

        while True:
            tick: RawTick = await self.queue.get()
            self._raw_count += 1

            try:
                normalized = self.normalizer.normalize(tick)

                if normalized:
                    await self.writer.write(normalized)
                    self._normalized_count += 1
                else:
                    self._dropped_count += 1
            except Exception as e:
                logger.error(f"Error normalizing tick: {e}")
                self._dropped_count += 1
            finally:
                self.queue.task_done()

    # ------------------------------------------------------------------
    # Stats logger
    # ------------------------------------------------------------------

    async def _stats_loop(self) -> None:
        """Log pipeline stats every 30 seconds for monitoring."""
        while True:
            await asyncio.sleep(30)

            uptime = time.time() - self._start_time
            rate = self._raw_count / uptime if uptime > 0 else 0

            logger.info(
                f"[stats] uptime={uptime:.0f}s | "
                f"raw={self._raw_count} | "
                f"normalized={self._normalized_count} | "
                f"dropped={self._dropped_count} | "
                f"rate={rate:.1f} ticks/s | "
                f"queue={self.queue.qsize()} | "
                f"redis={self.writer.stats}"
            )

    # ------------------------------------------------------------------
    # Health check data
    # ------------------------------------------------------------------

    @property
    def stats(self) -> dict:
        """Pipeline stats for the /health endpoint."""
        uptime = time.time() - self._start_time if self._start_time else 0
        return {
            "uptime_seconds": round(uptime),
            "raw_ticks": self._raw_count,
            "normalized_ticks": self._normalized_count,
            "dropped_ticks": self._dropped_count,
            "queue_depth": self.queue.qsize(),
            "redis": self.writer.stats,
            "connectors": {
                c.NAME: {"last_message": c.last_message_time}
                for c in self.connectors
            },
        }
