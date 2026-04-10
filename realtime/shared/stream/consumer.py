"""
Redis Stream consumer with consumer groups and batched reads.

Uses XREADGROUP for reliable, at-least-once delivery:
  - Consumer groups track read position automatically
  - Unacknowledged messages survive crashes (PEL)
  - Multiple consumers in the SAME group = load-balanced
  - Multiple consumer GROUPS = each gets independent copy
"""

import asyncio
import json
import logging
from typing import List, Tuple

import redis.asyncio as aioredis
from redis.exceptions import ResponseError

from shared.models import RawTick

logger = logging.getLogger(__name__)


class StreamConsumer:
    """
    Reads batches of RawTick events from a Redis Stream using
    consumer groups.
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        stream_key: str,
        group_name: str,
        consumer_name: str,
        batch_size: int = 100,
        block_ms: int = 2000,
    ):
        self._client = redis_client
        self._stream_key = stream_key
        self._group = group_name
        self._consumer = consumer_name
        self._batch_size = batch_size
        self._block_ms = block_ms

        self._consumed = 0
        self._acked = 0
        self._errors = 0

    async def setup(self) -> None:
        """Create the consumer group if it doesn't exist."""
        try:
            await self._client.xgroup_create(
                self._stream_key, self._group, id="$", mkstream=True,
            )
            logger.info(
                f"[stream-consumer] Created group '{self._group}' "
                f"on '{self._stream_key}'"
            )
        except ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.info(
                    f"[stream-consumer] Group '{self._group}' already exists "
                    f"— resuming from last position"
                )
            else:
                raise

    async def read_batch(self) -> List[Tuple[str, RawTick]]:
        """Read a batch of NEW messages from the stream."""
        try:
            response = await self._client.xreadgroup(
                self._group, self._consumer,
                {self._stream_key: ">"},
                count=self._batch_size, block=self._block_ms,
            )
        except Exception as e:
            logger.error(f"[stream-consumer] XREADGROUP failed: {e}")
            await asyncio.sleep(1)
            return []

        if not response:
            return []
        return self._parse_response(response)

    async def reclaim_pending(self) -> List[Tuple[str, RawTick]]:
        """Reclaim pending (unacknowledged) messages from a previous crash."""
        try:
            response = await self._client.xreadgroup(
                self._group, self._consumer,
                {self._stream_key: "0"},
                count=self._batch_size,
            )
        except Exception as e:
            logger.error(f"[stream-consumer] Reclaim failed: {e}")
            return []

        if not response:
            return []

        results = self._parse_response(response)
        if results:
            logger.info(f"[stream-consumer] Reclaimed {len(results)} pending messages")
        return results

    async def ack(self, message_ids: List[str]) -> None:
        """Acknowledge processed messages so they leave the PEL."""
        if not message_ids:
            return
        try:
            await self._client.xack(self._stream_key, self._group, *message_ids)
            self._acked += len(message_ids)
        except Exception as e:
            logger.error(f"[stream-consumer] XACK failed: {e}")

    def _parse_response(self, response: list) -> List[Tuple[str, RawTick]]:
        results = []
        for _stream_name, messages in response:
            for msg_id, fields in messages:
                if not fields:
                    continue
                try:
                    tick = self._deserialize(fields)
                    results.append((msg_id, tick))
                    self._consumed += 1
                except Exception as e:
                    logger.error(f"[stream-consumer] Deserialize failed for {msg_id}: {e}")
                    self._errors += 1
        return results

    @staticmethod
    def _deserialize(fields: dict) -> RawTick:
        return RawTick(
            exchange=fields["exchange"],
            pair=fields["pair"],
            data=json.loads(fields["data"]),
            received_at=float(fields["received_at"]),
        )

    @property
    def stats(self) -> dict:
        return {
            "consumed": self._consumed,
            "acknowledged": self._acked,
            "errors": self._errors,
        }
