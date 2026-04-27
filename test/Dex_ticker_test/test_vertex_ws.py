#!/usr/bin/env python3
"""
Vertex Protocol WebSocket smoke test.

Connects to Vertex's public websocket endpoint and subscribes to both
best bid/offer and trade updates for product_id 1.
"""

import asyncio
import json
from datetime import datetime

import websockets

WS_URL = "wss://gateway.prod.vertexprotocol.com/v1/ws"
# Vertex's current websocket endpoint as documented.

SUBSCRIPTIONS = [
    {
        "method": "subscribe",
        "stream": {
            "type": "best_bid_offer",
            "product_id": 1,
        },
        "id": 1,
    },
    {
        "method": "subscribe",
        "stream": {
            "type": "trade",
            "product_id": 1,
        },
        "id": 2,
    },
]

MAX_MESSAGES = 100


def format_message(raw: str) -> str:
    try:
        data = json.loads(raw)
        return json.dumps(data, indent=2)
    except Exception:
        return raw


async def main() -> None:
    print("=" * 72)
    print("  Vertex Protocol WebSocket Test")
    print("=" * 72)
    print(f"  URL: {WS_URL}")
    print("  Subscriptions:")
    for sub in SUBSCRIPTIONS:
        print("   -", json.dumps(sub))
    print("=" * 72)
    print()

    try:
        async with websockets.connect(WS_URL, ping_interval=20, open_timeout=15) as ws:
            print("✓ Connected to Vertex")

            for subscription in SUBSCRIPTIONS:
                payload = json.dumps(subscription)
                await ws.send(payload)
                print(f"✓ Sent: {payload}")
            print()
            print("Waiting for messages (Ctrl+C to stop)...")
            print("-" * 72)

            count = 0
            async for message in ws:
                count += 1
                output = format_message(message)
                timestamp = datetime.utcnow().strftime("%H:%M:%S")
                print(f"[{timestamp}] message #{count}\n{output}\n")
                if count >= MAX_MESSAGES:
                    print(f"Reached {MAX_MESSAGES} messages. Exiting.")
                    break

    except websockets.exceptions.ConnectionClosed as e:
        print(f"\n✗ Connection closed: {e}")
    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n✓ Test stopped by user")
