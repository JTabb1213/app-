#!/usr/bin/env python3
"""
PancakeSwap connectivity smoke test using a BSC WebSocket node.

This script connects to a public BSC websocket endpoint and subscribes to
new block headers. It is useful for validating that the chain/DEX data
transport is reachable.
"""

import asyncio
import json
from datetime import datetime

import websockets

WS_URL = "wss://bsc-ws-node.nariox.org:443"
SUBSCRIBE_MESSAGE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "eth_subscribe",
    "params": ["newHeads"],
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
    print("  PancakeSwap / BSC WebSocket Test")
    print("=" * 72)
    print(f"  URL: {WS_URL}")
    print(f"  Subscribe: {SUBSCRIBE_MESSAGE['method']}")
    print("=" * 72)
    print()

    try:
        async with websockets.connect(WS_URL, ping_interval=20, open_timeout=20) as ws:
            print("✓ Connected to BSC WebSocket")
            await ws.send(json.dumps(SUBSCRIBE_MESSAGE))
            print("✓ Sent eth_subscribe(newHeads)")
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
