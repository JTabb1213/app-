#!/usr/bin/env python3
"""
Trade Collectors-Primary Service
==================================

Connects to Kraken, Coinbase, and Binance TRADE websocket feeds
and pushes raw trade executions to the Redis Stream for volume aggregation.

Unlike the ticker collectors (collectors-primary), this service subscribes
to individual trade/match channels, not ticker channels.

Usage:
    cd realtime/trade-collectors-primary
    python main.py
"""

import asyncio
import logging
import sys
import os

_parent = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
if os.path.isdir(os.path.join(_parent, "shared")):
    sys.path.insert(0, _parent)

from aiohttp import web
import redis.asyncio as aioredis

import config
from shared.stream.producer import StreamProducer
from exchanges.binance_trades import BinanceTradeConnector
from exchanges.coinbase_trades import CoinbaseTradeConnector
from exchanges.kraken_trades import KrakenTradeConnector

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s │ %(levelname)-7s │ %(name)-20s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("trade-collectors-primary")
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.ERROR)

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
_connectors = []
_producer = None


async def _health_handler(request):
    info = {
        "status": "healthy",
        "service": "trade-collectors-primary",
        "exchanges": ["kraken", "coinbase", "binance"],
        "producer": _producer.stats if _producer else {},
        "connectors": {
            c.NAME: {"last_message": c.last_message_time}
            for c in _connectors
        },
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
# Main
# ---------------------------------------------------------------------------
async def main():
    global _connectors, _producer

    logger.info("=" * 60)
    logger.info("  Trade Collectors-Primary (Kraken, Coinbase, Binance)")
    logger.info("=" * 60)

    if not config.REDIS_URL:
        raise ValueError("REDIS_URL is not set.")

    redis_client = aioredis.from_url(config.REDIS_URL, decode_responses=True)
    await redis_client.ping()
    logger.info("Connected to Redis")

    _producer = StreamProducer(
        redis_client=redis_client,
        stream_key=config.STREAM_KEY,
        batch_size=config.STREAM_PRODUCER_BATCH_SIZE,
        flush_interval_ms=config.STREAM_PRODUCER_FLUSH_MS,
        max_stream_len=config.STREAM_MAX_LEN,
    )

    kraken = KrakenTradeConnector(_producer)
    coinbase = CoinbaseTradeConnector(_producer)
    binance = BinanceTradeConnector(_producer)
    _connectors = [kraken, coinbase, binance]

    await _start_health_server()

    tasks = [
        asyncio.create_task(c.run(), name=f"connector:{c.NAME}")
        for c in _connectors
    ]
    tasks.append(asyncio.create_task(_producer.flush_loop(), name="producer-flush"))

    logger.info(f"Running {len(_connectors)} connector(s): {[c.NAME for c in _connectors]}")

    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
    for t in done:
        if t.exception():
            logger.error(f"Task '{t.get_name()}' crashed: {t.exception()}")
    for t in pending:
        t.cancel()

    await redis_client.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)
