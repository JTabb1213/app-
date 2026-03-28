#!/usr/bin/env python3
"""Quick test client for the WS broadcast server."""
import asyncio
import json
import pathlib
import websockets

COIN_ALIASES_PATH = pathlib.Path(__file__).resolve().parents[1] / "data" / "coin_aliases.json"

async def test():
    with open(COIN_ALIASES_PATH, "r", encoding="utf-8") as f:
        coins = list(json.load(f).get("assets", {}).keys())

    if not coins:
        raise RuntimeError("No coins found in data/coin_aliases.json")

    async with websockets.connect("ws://localhost:8765") as ws:
        # Subscribe
        await ws.send(json.dumps({
            "action": "subscribe",
            "channel": "prices",
            "coins": coins
        }))
        ack = await ws.recv()
        print(f"ACK: {ack}")

        # Wait for ticks
        print("Waiting for ticks (Ctrl+C to stop)...")
        try:
            for _ in range(10):
                msg = await asyncio.wait_for(ws.recv(), timeout=15)
                data = json.loads(msg)
                coin = data["data"]["coin_id"]
                price = data["data"]["price"]
                print(f"  TICK: {coin} = ${price:,.2f}")
        except asyncio.TimeoutError:
            print("  No ticks received (is the realtime service running?)")

        # Test unsubscribe
        await ws.send(json.dumps({
            "action": "unsubscribe",
            "channel": "prices",
            "coins": ["cardano"]
        }))
        unsub_ack = await ws.recv()
        print(f"UNSUB ACK: {unsub_ack}")

        # Test error
        await ws.send(json.dumps({"action": "subscribe", "channel": "fake"}))
        err = await ws.recv()
        print(f"ERROR: {err}")

asyncio.run(test())
