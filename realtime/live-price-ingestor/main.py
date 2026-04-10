#!/usr/bin/env python3
"""
Ingestor Service
=================

Reads raw tick data from the Redis Stream, normalizes it
(alias resolution, field mapping), computes multi-exchange
aggregates, and publishes results to Redis cache + pub/sub.

This service does NOT connect to any exchange websockets.
It only consumes from the shared Redis Stream that the
collector services produce into.

Usage:
    cd realtime/ingestor
    python main.py
"""

import asyncio
import logging
import sys
import os
import time
from typing import List, Tuple

# ── Make 'shared' package importable ──────────────────────────────────────
_parent = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
if os.path.isdir(os.path.join(_parent, "shared")):
    sys.path.insert(0, _parent)

from aiohttp import web
import redis.asyncio as aioredis

import config
from shared.models import RawTick
from shared.stream.consumer import StreamConsumer
from normalizer.normalizer import Normalizer
from normalizer.aliases import AliasResolver
from storage.redis_writer import RedisWriter

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s │ %(levelname)-7s │ %(name)-20s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ingestor")
logging.getLogger("aiohttp").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Pipeline stats
# ---------------------------------------------------------------------------
_consumer: StreamConsumer = None
_writer: RedisWriter = None
_raw_count = 0
_normalized_count = 0
_dropped_count = 0
_start_time = 0.0


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
async def _health_handler(request):
    uptime = time.time() - _start_time if _start_time else 0
    info = {
        "status": "healthy",
        "service": "ingestor",
        "uptime_seconds": round(uptime),
        "raw_ticks": _raw_count,
        "normalized_ticks": _normalized_count,
        "dropped_ticks": _dropped_count,
        "consumer": _consumer.stats if _consumer else {},
        "writer": _writer.stats if _writer else {},
    }
    return web.json_response(info)


async def _start_health_server():
    app = web.Application()
    app.router.add_get("/health", _health_handler)
    app.router.add_get("/", _health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", config.HEALTH_PORT)
    await site.start()
    logger.info(f"Health check listening on :{config.HEALTH_PORT}")


# ---------------------------------------------------------------------------
# Consumer loop
# ---------------------------------------------------------------------------
async def _consume_loop(
    consumer: StreamConsumer,
    normalizer: Normalizer,
    writer: RedisWriter,
):
    """
    Main consumer loop: reads batches from Redis Stream,
    normalizes, and writes to Redis cache.
    """
    global _raw_count, _normalized_count, _dropped_count

    logger.info("Stream consumer started")

    # ── Crash recovery: process any unacknowledged messages ──
    pending = await consumer.reclaim_pending()
    if pending:
        await _process_batch(pending, normalizer, writer, consumer)
        logger.info(f"Recovered {len(pending)} pending messages from previous run")

    # ── Main loop ──
    logger.info("Consuming new messages from stream...")

    while True:
        batch = await consumer.read_batch()
        if batch:
            await _process_batch(batch, normalizer, writer, consumer)


async def _process_batch(
    batch: List[Tuple[str, RawTick]],
    normalizer: Normalizer,
    writer: RedisWriter,
    consumer: StreamConsumer,
):
    """Normalize a batch of raw ticks and feed to the Redis writer."""
    global _raw_count, _normalized_count, _dropped_count

    msg_ids = []

    for msg_id, tick in batch:
        msg_ids.append(msg_id)
        _raw_count += 1

        try:
            normalized = normalizer.normalize(tick)
            if normalized:
                await writer.write(normalized)
                _normalized_count += 1
            else:
                _dropped_count += 1
        except Exception as e:
            logger.error(f"Error normalizing tick: {e}")
            _dropped_count += 1

    # ACK the entire batch at once
    await consumer.ack(msg_ids)


# ---------------------------------------------------------------------------
# Stats logger
# ---------------------------------------------------------------------------
async def _stats_loop():
    """Log pipeline stats every 30 seconds."""
    while True:
        await asyncio.sleep(30)
        uptime = time.time() - _start_time if _start_time else 0
        rate = _raw_count / uptime if uptime > 0 else 0
        logger.info(
            f"[stats] uptime={uptime:.0f}s | "
            f"raw={_raw_count} | "
            f"normalized={_normalized_count} | "
            f"dropped={_dropped_count} | "
            f"rate={rate:.1f} ticks/s | "
            f"consumer={_consumer.stats if _consumer else {}} | "
            f"writer={_writer.stats if _writer else {}}"
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    global _consumer, _writer, _start_time

    _start_time = time.time()

    logger.info("=" * 60)
    logger.info("  Ingestor (Stream Consumer → Normalize → Redis)")
    logger.info("=" * 60)

    if not config.REDIS_URL:
        raise ValueError("REDIS_URL is not set.")

    redis_client = aioredis.from_url(config.REDIS_URL, decode_responses=True)
    await redis_client.ping()
    logger.info("Connected to Redis")

    # Stream consumer
    _consumer = StreamConsumer(
        redis_client=redis_client,
        stream_key=config.STREAM_TRADES_KEY,
        group_name=config.STREAM_CONSUMER_GROUP,
        consumer_name=config.STREAM_CONSUMER_NAME,
        batch_size=config.STREAM_CONSUMER_BATCH_SIZE,
        block_ms=config.STREAM_CONSUMER_BLOCK_MS,
    )
    await _consumer.setup()

    # Normalizer
    alias_resolver = AliasResolver()
    normalizer = Normalizer(alias_resolver)

    # Redis writer (includes aggregator internally)
    _writer = RedisWriter()
    await _writer.connect()

    await _start_health_server()

    tasks = [
        asyncio.create_task(
            _consume_loop(_consumer, normalizer, _writer),
            name="consume-loop",
        ),
        asyncio.create_task(
            _writer.flush_loop(),
            name="writer-flush",
        ),
        asyncio.create_task(
            _stats_loop(),
            name="stats",
        ),
    ]

    logger.info("Ingestor running — consuming from stream:trades")

    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
    for t in done:
        if t.exception():
            logger.error(f"Task '{t.get_name()}' crashed: {t.exception()}")
    for t in pending:
        t.cancel()

    await _writer.close()
    await redis_client.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)
