"""
Redis pub/sub listener.

Subscribes to one or more Redis channels and routes incoming
messages to the appropriate Channel handler.
"""

import asyncio
import logging

import redis.asyncio as aioredis

import config
from channels.base import Channel

logger = logging.getLogger(__name__)


class RedisSubscriber:
    """
    Listens on Redis pub/sub and dispatches messages to Channel objects.

    Each Channel declares its own redis_channel name (e.g. "rt:stream:prices").
    This class subscribes to all of them and routes accordingly.
    """

    def __init__(self, channels: list[Channel]):
        self._channels = channels
        # redis_channel_name → Channel instance for fast dispatch
        self._dispatch: dict[str, Channel] = {
            ch.redis_channel: ch for ch in channels
        }
        self._client: aioredis.Redis = None
        self._pubsub: aioredis.client.PubSub = None

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

        logger.info(
            f"Redis pub/sub connected — listening on: {channel_names}"
        )

    async def listen(self) -> None:
        """
        Main listen loop — runs forever, dispatching messages to channels.

        Should be started as an asyncio task from main.py.
        """
        async for message in self._pubsub.listen():
            if message["type"] != "message":
                continue

            redis_channel = message["channel"]
            handler = self._dispatch.get(redis_channel)
            if handler:
                await handler.route(message["data"])

    async def close(self) -> None:
        """Unsubscribe and close Redis connection."""
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.aclose()
        if self._client:
            await self._client.aclose()
        logger.info("Redis pub/sub connection closed")
