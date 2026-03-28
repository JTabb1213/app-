"""
Abstract base class for WS broadcast channels.

A "channel" represents a category of real-time data that clients can
subscribe to — prices, order books, whale alerts, etc.

To add a new channel:
  1. Create a new file in channels/ (e.g. orders.py)
  2. Subclass Channel
  3. Implement redis_channel, handle_subscribe, handle_unsubscribe, route
  4. Register it in main.py

Each channel owns its own subscription routing dict so channels
are fully independent and don't interfere with each other.
"""

from abc import ABC, abstractmethod
from typing import Set
import websockets
import json
import logging

logger = logging.getLogger(__name__)


class Channel(ABC):
    """Base class for a subscribable data channel."""

    def __init__(self):
        # coin_id → set of websocket connections subscribed to that coin
        self._subscriptions: dict[str, Set[websockets.WebSocketServerProtocol]] = {}

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable channel name, e.g. 'prices'."""
        ...

    @property
    @abstractmethod
    def redis_channel(self) -> str:
        """Redis pub/sub channel to listen on, e.g. 'rt:stream:prices'."""
        ...

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------

    def subscribe(self, ws: websockets.WebSocketServerProtocol, coins: list[str]) -> list[str]:
        """
        Subscribe a client to a list of coins on this channel.
        Returns the list of coins actually subscribed.
        """
        subscribed = []
        for coin_id in coins:
            coin_id = coin_id.strip().lower()
            if not coin_id:
                continue
            if coin_id not in self._subscriptions:
                self._subscriptions[coin_id] = set()
            self._subscriptions[coin_id].add(ws)
            subscribed.append(coin_id)
        return subscribed

    def unsubscribe(self, ws: websockets.WebSocketServerProtocol, coins: list[str]) -> list[str]:
        """
        Unsubscribe a client from a list of coins on this channel.
        Returns the list of coins actually unsubscribed.
        """
        unsubscribed = []
        for coin_id in coins:
            coin_id = coin_id.strip().lower()
            subs = self._subscriptions.get(coin_id)
            if subs and ws in subs:
                subs.discard(ws)
                if not subs:
                    del self._subscriptions[coin_id]
                unsubscribed.append(coin_id)
        return unsubscribed

    def remove_client(self, ws: websockets.WebSocketServerProtocol) -> None:
        """Remove a client from ALL subscriptions on this channel (on disconnect)."""
        empty_keys = []
        for coin_id, subs in self._subscriptions.items():
            subs.discard(ws)
            if not subs:
                empty_keys.append(coin_id)
        for key in empty_keys:
            del self._subscriptions[key]

    # ------------------------------------------------------------------
    # Message routing
    # ------------------------------------------------------------------

    async def route(self, message: str) -> None:
        """
        Route a Redis pub/sub message to the correct subscribers.

        The message is a JSON string. We extract the routing key
        (e.g. coin_id) and send only to clients subscribed to that key.
        """
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            logger.warning(f"[{self.name}] Invalid JSON from Redis: {message[:100]}")
            return

        routing_key = self._extract_routing_key(data)
        if not routing_key:
            return

        subscribers = self._subscriptions.get(routing_key, set())
        if not subscribers:
            return

        # Wrap with channel name so client knows what type of message this is
        outgoing = json.dumps({"channel": self.name, "data": data})

        # Fan out — send to all subscribers concurrently
        disconnected = set()
        for ws in subscribers:
            try:
                await ws.send(outgoing)
            except websockets.ConnectionClosed:
                disconnected.add(ws)

        # Clean up any connections that died mid-send
        for ws in disconnected:
            self.remove_client(ws)

    @abstractmethod
    def _extract_routing_key(self, data: dict) -> str | None:
        """
        Extract the routing key from a parsed message.
        For prices this is data["coin_id"], for orders it might be
        data["pair"], etc.
        """
        ...

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @property
    def stats(self) -> dict:
        total_subs = sum(len(s) for s in self._subscriptions.values())
        return {
            "channel": self.name,
            "coins_tracked": len(self._subscriptions),
            "total_subscriptions": total_subs,
        }
