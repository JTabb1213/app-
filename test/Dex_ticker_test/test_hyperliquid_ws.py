#!/usr/bin/env python3
"""
Hyperliquid WebSocket smoke test.

Connects to Hyperliquid's public market feed and prints raw messages.
Adjust WS_URL and SUBSCRIBE_MESSAGE to match the current Hyperliquid API.
"""

import asyncio
import json
from datetime import datetime

import websockets

WS_URL = "wss://api.hyperliquid.xyz/ws"
SUBSCRIBE_MESSAGE = {
    "method": "subscribe",
    "subscription": {
        "type": "allMids",
    },
}

MAX_MESSAGES = 100


def format_message(raw: str) -> str:
    try:
        data = json.loads(raw)
        return json.dumps(data, indent=2)
    except Exception:
        return raw


async def main() -> None:
    print("=" * 72)
    print("  Hyperliquid WebSocket Test")
    print("=" * 72)
    print(f"  URL: {WS_URL}")
    print("=" * 72)
    print()

    try:
        async with websockets.connect(WS_URL, ping_interval=20, open_timeout=15) as ws:
            print("✓ Connected to Hyperliquid")

            if SUBSCRIBE_MESSAGE is not None:
                payload = json.dumps(SUBSCRIBE_MESSAGE)
                await ws.send(payload)
                print("✓ Sent subscribe payload")
                print(payload)
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
