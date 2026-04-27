#!/usr/bin/env python3
"""
WebSocket broadcast server — entry point.

Reads live data from Redis pub/sub and fans it out to subscribed
WebSocket clients.  Each data type (prices, orders, whale alerts, etc.)
is handled by a Channel class in the channels/ package.

Usage:
    python main.py

Environment:
    REDIS_URL       Redis connection string (required)
    WS_PORT         WebSocket port (default: 8765)
    HEALTH_PORT     Health check HTTP port (default: 8080)
    LOG_LEVEL       Logging level (default: INFO)
"""

import asyncio
import logging
import signal
import sys
from http import HTTPStatus

import websockets

import config
from channels.prices import PriceChannel
from redis_sub import RedisSubscriber
from server import ConnectionHandler, connected_clients

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s │ %(levelname)-7s │ %(name)-20s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ws")


# ---------------------------------------------------------------------------
# Health check (simple HTTP for load balancer / container probes)
# ---------------------------------------------------------------------------
async def health_handler(reader, writer):
    """Respond to any TCP connection with a 200 OK."""
    request = await reader.read(1024)
    body = f'{{"status":"ok","clients":{len(connected_clients)}}}'
    response = (
        f"HTTP/1.1 200 OK\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"\r\n{body}"
    )
    writer.write(response.encode())
    await writer.drain()
    writer.close()


async def start_health_server():
    server = await asyncio.start_server(health_handler, "0.0.0.0", config.HEALTH_PORT)
    logger.info(f"Health check listening on :{config.HEALTH_PORT}")
    return server


async def process_request(connection, request):
    """Handle HTTP health-check requests on the WebSocket port.

    Cloud Run (and other container platforms) probe the single exposed port
    with a plain HTTP GET.  We respond to /health and /healthz so startup
    probes pass; all other paths (including /) fall through to WebSocket handshake.
    """
    if request.path in ("/health", "/healthz"):
        body = f'{{"status":"ok","clients":{len(connected_clients)}}}'
        return connection.respond(HTTPStatus.OK, body)
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    logger.info("=" * 60)
    logger.info("  WebSocket Broadcast Server")
    logger.info("=" * 60)

    # -- 1. Register channels -----------------------------------------------
    # Add new channels here as you build them (orders, whale alerts, etc.)
    price_channel = PriceChannel()
    all_channels = [price_channel]

    channel_map = {ch.name: ch for ch in all_channels}
    logger.info(f"Channels registered: {list(channel_map.keys())}")

    # -- 2. Connect to Redis pub/sub ----------------------------------------
    redis_sub = RedisSubscriber(all_channels)
    await redis_sub.connect()

    # -- 3. Start WebSocket server -------------------------------------------
    # Each new connection gets its own ConnectionHandler instance
    async def on_connect(ws):
        handler = ConnectionHandler(channel_map)
        await handler.handle(ws)

    ws_server = await websockets.serve(
        on_connect,
        config.WS_HOST,
        config.WS_PORT,
        ping_interval=20,
        ping_timeout=10,
        process_request=process_request,
    )
    logger.info(f"WebSocket server listening on ws://{config.WS_HOST}:{config.WS_PORT}")

    # -- 4. Start health check (extra TCP port for VM/bare-metal deployments) --
    # On Cloud Run only one port is exposed (WS_PORT), so this may be
    # unreachable externally — that's fine, health checks hit / on WS_PORT.
    health_server = await start_health_server()

    # -- 5. Start Redis listener (runs forever) ------------------------------
    redis_task = asyncio.create_task(redis_sub.listen())
    logger.info("Listening for Redis pub/sub messages...")

    # -- 6. Graceful shutdown ------------------------------------------------
    stop = asyncio.Event()

    def signal_handler():
        logger.info("Shutdown signal received")
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    await stop.wait()

    # Cleanup
    logger.info("Shutting down...")
    redis_task.cancel()
    ws_server.close()
    await ws_server.wait_closed()
    health_server.close()
    await health_server.wait_closed()
    await redis_sub.close()
    logger.info("Goodbye.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
