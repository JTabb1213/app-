"""
WebSocket connection handler.

Manages client connections, parses subscribe/unsubscribe messages,
and delegates to the appropriate Channel.

Client protocol:
    → { "action": "subscribe",   "channel": "prices", "coins": ["bitcoin", "ethereum"] }
    → { "action": "unsubscribe", "channel": "prices", "coins": ["bitcoin"] }
    ← { "channel": "prices", "data": { ... } }              (price tick)
    ← { "type": "subscribed",   "channel": "prices", "coins": [...] }  (ack)
    ← { "type": "unsubscribed", "channel": "prices", "coins": [...] }  (ack)
    ← { "type": "error", "message": "..." }                            (error)
"""

import json
import logging
from typing import Dict

import websockets

import config
from channels.base import Channel

logger = logging.getLogger(__name__)

# Track all connected clients for stats / broadcasting
connected_clients: set[websockets.WebSocketServerProtocol] = set()


class ConnectionHandler:
    """
    Handles the lifecycle of a single WebSocket connection.

    Each connected client gets one instance. It parses incoming
    messages and routes subscribe/unsubscribe actions to the
    correct Channel.
    """

    def __init__(self, channels: Dict[str, Channel]):
        # channel_name → Channel instance
        self._channels = channels
        # Track what this specific client is subscribed to (for limit enforcement)
        self._client_sub_count: int = 0

    async def handle(self, ws: websockets.WebSocketServerProtocol) -> None:
        """Main handler — called once per client connection."""
        connected_clients.add(ws)
        remote = ws.remote_address
        logger.info(f"Client connected: {remote} ({len(connected_clients)} total)")

        try:
            async for raw_message in ws:
                await self._process_message(ws, raw_message)
        except websockets.ConnectionClosed:
            pass
        finally:
            # Clean up subscriptions across ALL channels
            for channel in self._channels.values():
                channel.remove_client(ws)
            connected_clients.discard(ws)
            logger.info(f"Client disconnected: {remote} ({len(connected_clients)} total)")

    async def _process_message(
        self,
        ws: websockets.WebSocketServerProtocol,
        raw: str,
    ) -> None:
        """Parse and dispatch a single client message."""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            await self._send_error(ws, "Invalid JSON")
            return

        action = msg.get("action")
        channel_name = msg.get("channel")
        coins = msg.get("coins", [])

        if not action or not channel_name:
            await self._send_error(ws, "Missing 'action' or 'channel' field")
            return

        channel = self._channels.get(channel_name)
        if not channel:
            available = list(self._channels.keys())
            await self._send_error(ws, f"Unknown channel '{channel_name}'. Available: {available}")
            return

        if not isinstance(coins, list) or not coins:
            await self._send_error(ws, "'coins' must be a non-empty list of canonical IDs")
            return

        if action == "subscribe":
            # Enforce per-client subscription limit
            new_count = self._client_sub_count + len(coins)
            if new_count > config.MAX_SUBSCRIPTIONS_PER_CLIENT:
                await self._send_error(
                    ws,
                    f"Subscription limit exceeded. Max {config.MAX_SUBSCRIPTIONS_PER_CLIENT} "
                    f"(current: {self._client_sub_count}, requested: {len(coins)})"
                )
                return

            subscribed = channel.subscribe(ws, coins)
            self._client_sub_count += len(subscribed)
            await ws.send(json.dumps({
                "type": "subscribed",
                "channel": channel_name,
                "coins": subscribed,
            }))
            logger.debug(f"[{ws.remote_address}] subscribed to {channel_name}: {subscribed}")

        elif action == "unsubscribe":
            unsubscribed = channel.unsubscribe(ws, coins)
            self._client_sub_count = max(0, self._client_sub_count - len(unsubscribed))
            await ws.send(json.dumps({
                "type": "unsubscribed",
                "channel": channel_name,
                "coins": unsubscribed,
            }))
            logger.debug(f"[{ws.remote_address}] unsubscribed from {channel_name}: {unsubscribed}")

        else:
            await self._send_error(ws, f"Unknown action '{action}'. Use 'subscribe' or 'unsubscribe'")

    @staticmethod
    async def _send_error(ws: websockets.WebSocketServerProtocol, message: str) -> None:
        await ws.send(json.dumps({"type": "error", "message": message}))
