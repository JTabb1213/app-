"""
Redis pub/sub listener with automatic reconnection.

Subscribes to one or more Redis channels and routes incoming
messages to the appropriate Channel handler.  Reconnects with
exponential backoff if the connection drops.
"""

import asyncio
import logging
import time

import redis.asyncio as aioredis

import config
from channels.base import Channel

logger = logging.getLogger(__name__)

# How long (seconds) with no messages before logging a staleness warning
STALENESS_TIMEOUT = int(getattr(config, "PUBSUB_STALENESS_TIMEOUT", 60))
# Max reconnect backoff in seconds
MAX_BACKOFF = 60


class RedisSubscriber:
    """
    Listens on Redis pub/sub and dispatches messages to Channel objects.

    Each Channel declares its own redis_channel name (e.g. "rt:stream:prices").
    This class subscribes to all of them and routes accordingly.
    Automatically reconnects on connection loss.
    """

    def __init__(self, channels: list[Channel]):
        self._channels = channels
        # redis_channel_name → Channel instance for fast dispatch
        self._dispatch: dict[str, Channel] = {
            ch.redis_channel: ch for ch in channels
        }
        self._client: aioredis.Redis = None
        self._pubsub: aioredis.client.PubSub = None
        self._last_message_time: float = 0.0

    async def connect(self) -> None:
        """Connect to Redis and subscribe to all channel topics."""
        if not config.REDIS_URL:
            raise ValueError(
                "REDIS_URL is not set. "
                "Copy .env.example to .env and add your Redis URL."
            )

        self._client = aioredis.from_url(
            config.REDIS_URL,
            decode_responses=True,
        )
        await self._client.ping()

        self._pubsub = self._client.pubsub()
        channel_names = list(self._dispatch.keys())
        await self._pubsub.subscribe(*channel_names)
        self._last_message_time = time.time()

        logger.info(
            f"Redis pub/sub connected — listening on: {channel_names}"
        )

    async def listen(self) -> None:
        """
        Main listen loop — runs forever with automatic reconnection.

        If the pub/sub connection drops, reconnects with exponential backoff.
        Logs a warning if no messages arrive for STALENESS_TIMEOUT seconds.
        """
        backoff = 1

        while True:
            try:
                await self._listen_inner()
            except Exception as e:
                logger.error(
                    f"Redis pub/sub connection lost: {e}. "
                    f"Reconnecting in {backoff}s..."
                )
                # Clean up old connection
                await self._safe_close()
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF)

                try:
                    await self.connect()
                    logger.info("Redis pub/sub reconnected successfully")
                    backoff = 1  # reset on success
                except Exception as reconnect_err:
                    logger.error(f"Redis pub/sub reconnect failed: {reconnect_err}")

    async def _listen_inner(self) -> None:
        """Core listen loop — raises on connection errors."""
        staleness_logged = False

        while True:
            # Check for staleness
            elapsed = time.time() - self._last_message_time
            if elapsed > STALENESS_TIMEOUT and not staleness_logged:
                logger.warning(
                    f"No pub/sub messages received for {elapsed:.0f}s — "
                    f"possible stale connection"
                )
                staleness_logged = True

            try:
                message = await asyncio.wait_for(
                    self._pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=5.0
                    ),
                    timeout=10.0,
                )
            except asyncio.TimeoutError:
                continue

            if message is None:
                continue

            if message["type"] != "message":
                continue

            self._last_message_time = time.time()
            staleness_logged = False

            redis_channel = message["channel"]
            handler = self._dispatch.get(redis_channel)
            if handler:
                await handler.route(message["data"])

    async def _safe_close(self) -> None:
        """Close existing connections without raising."""
        try:
            if self._pubsub:
                await self._pubsub.unsubscribe()
                await self._pubsub.aclose()
        except Exception:
            pass
        try:
            if self._client:
                await self._client.aclose()
        except Exception:
            pass
        self._pubsub = None
        self._client = None

    async def close(self) -> None:
        """Unsubscribe and close Redis connection."""
        await self._safe_close()
        logger.info("Redis pub/sub connection closed")
