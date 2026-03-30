"""
Realtime Market Data Ingestion Server
======================================

Connects to cryptocurrency exchange websockets, normalizes incoming
market data into a unified format, and writes it to Redis for the
API layer to serve.

Architecture:
    Exchange Connectors → Ingestion Queue → Normalizer → Batch Buffer → Redis Pipeline

Usage:
    python main.py

Environment:
    See .env.example for required configuration.
"""

import asyncio
import logging
import sys

from aiohttp import web

import config
from core.pipeline import Pipeline
from exchanges.kraken import KrakenConnector
from exchanges.coinbase import CoinbaseConnector
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
logger = logging.getLogger("realtime")

# Silence noisy libraries
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Health check server
# ---------------------------------------------------------------------------
# Cloud Run requires an HTTP endpoint to verify the container is alive.
# This tiny aiohttp server exposes /health with pipeline stats.
# ---------------------------------------------------------------------------
_pipeline: Pipeline = None   # set in main(), read by health handler


async def _health_handler(request):
    """Health check endpoint for Cloud Run / load balancers."""
    if _pipeline:
        return web.json_response({
            "status": "healthy",
            "stats": _pipeline.stats,
        })
    return web.json_response({"status": "starting"}, status=503)


async def _start_health_server():
    """Start a minimal HTTP server for health/readiness probes."""
    app = web.Application()
    app.router.add_get("/health", _health_handler)
    app.router.add_get("/", _health_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", config.HEALTH_PORT)
    await site.start()
    logger.info(f"Health check server listening on :{config.HEALTH_PORT}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    global _pipeline

    logger.info("=" * 60)
    logger.info("  Realtime Market Data Ingestion Server")
    logger.info("=" * 60)

    # 1. Alias resolver — loads data/coin_aliases.json into memory
    alias_resolver = AliasResolver()
    logger.info(
        f"Alias resolver: {alias_resolver.total_assets} assets, "
        f"{alias_resolver.total_aliases} aliases"
    )

    # 2. Normalizer — converts exchange-specific data to canonical format
    normalizer = Normalizer(alias_resolver)

    # 3. Redis writer — batched pipeline writes
    writer = RedisWriter()
    await writer.connect()

    # 4. Ingestion queue — decouples websocket receiving from processing
    #    maxsize prevents unbounded memory growth if processing falls behind
    ingestion_queue = asyncio.Queue(maxsize=10_000)

    # 5. Exchange connectors
    #    Add more exchanges here as you build them:
    #      binance  = BinanceConnector(ingestion_queue)
    kraken = KrakenConnector(ingestion_queue)
    coinbase = CoinbaseConnector(ingestion_queue)
    connectors = [kraken, coinbase]

    # 6. Wire up the pipeline
    _pipeline = Pipeline(
        connectors=connectors,
        normalizer=normalizer,
        writer=writer,
        queue=ingestion_queue,
    )

    # 7. Start health check server + pipeline
    await _start_health_server()

    try:
        await _pipeline.run()
    finally:
        await writer.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)
