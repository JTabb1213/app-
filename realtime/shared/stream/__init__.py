"""
Redis Streams abstraction layer.

Producer: exchange connectors → in-memory buffer → batched XADD → Redis Stream
Consumer: Redis Stream → XREADGROUP (batched) → process → XACK
"""

from .producer import StreamProducer
from .consumer import StreamConsumer

__all__ = ["StreamProducer", "StreamConsumer"]
