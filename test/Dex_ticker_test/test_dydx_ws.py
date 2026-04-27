#!/usr/bin/env python3
"""
dYdX v4 WebSocket smoke test.

Connects to the dYdX indexer websocket and subscribes to order book and
trade channels for BTC-USD.
"""

import asyncio
import json
from datetime import datetime

import websockets

WS_URL = "wss://indexer.dydx.trade/v4/ws"
SUBSCRIPTIONS = [
    {
        "type": "subscribe",
        "channel": "v4_ticker",
        "id": "BTC-USD",
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
    print("  dYdX v4 WebSocket Test")
    print("=" * 72)
    print(f"  URL: {WS_URL}")
    print("  Subscriptions:")
    for sub in SUBSCRIPTIONS:
        print("   -", json.dumps(sub))
    print("=" * 72)
    print()

    try:
        async with websockets.connect(WS_URL, ping_interval=20, open_timeout=15) as ws:
            print("✓ Connected to dYdX")

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
