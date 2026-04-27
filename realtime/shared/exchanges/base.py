"""
Abstract base class for exchange websocket connectors.

Every exchange connector must:
  1. Connect to the exchange's websocket API
  2. Parse incoming messages into RawTick events
  3. Push RawTick events to the StreamProducer (in-memory buffer → Redis Stream)

To add a new exchange:
  1. Create a new file in your service's exchanges/ folder
  2. Subclass BaseExchange
  3. Implement _connect_and_stream()
  4. Register it in your service's main.py connector list
"""

import asyncio
import logging
from abc import ABC, abstractmethod

from shared.models import RawTick
from shared.stream.producer import StreamProducer

logger = logging.getLogger(__name__)


class BaseExchange(ABC):
    """
    Abstract base for all exchange websocket connectors.

    Handles:
      - Reconnection with exponential backoff
      - Pushing parsed RawTick events to the stream producer buffer
      - Health tracking (last message timestamp)

    Subclasses only need to implement _connect_and_stream().
    """

    NAME: str = "unknown"

    def __init__(self, producer: StreamProducer):
        self._producer = producer
        self.last_message_time: float = 0
        self._running = False

    @abstractmethod
    async def _connect_and_stream(self) -> None:
        ...

    async def _emit(self, tick: RawTick) -> None:
        """Push a parsed tick into the stream producer's buffer."""
        await self._producer.put(tick)
        self.last_message_time = tick.received_at

    async def run(self) -> None:
        """Run the connector forever with automatic reconnection."""
        self._running = True
        backoff = 1

        while self._running:
            try:
                logger.info(f"[{self.NAME}] Connecting...")
                await self._connect_and_stream()
            except Exception as e:
                logger.error(
                    f"[{self.NAME}] Connection error: {e}. "
                    f"Reconnecting in {backoff}s..."
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
            else:
                backoff = 1

    def stop(self) -> None:
        """Signal the connector to stop."""
        self._running = False
