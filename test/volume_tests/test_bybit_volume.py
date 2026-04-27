#!/usr/bin/env python3
"""
Bybit raw trade-volume subscription test.

Subscribes to Bybit's public trade feed for all USDT pairs from
data/coin_aliases.json and logs the first 50 raw messages.
"""

import asyncio
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from volume_symbols import bybit_symbols

try:
    import websockets
except ImportError:
    print("ERROR: 'websockets' package not found. Run: pip install websockets")
    raise SystemExit(1)

WS_URL = "wss://stream.bybit.com/v5/public/spot"
SYMBOLS = bybit_symbols()
LOG_PATH = ROOT / f"{pathlib.Path(__file__).stem}.log"

async def main() -> None:
    print(f"Connecting to Bybit with {len(SYMBOLS)} USDT pairs")
    print(f"Logging first 50 messages to {LOG_PATH}")
    async with websockets.connect(WS_URL, ping_interval=20) as ws:
        # Bybit limits to 10 args per subscribe message
        args = [f"publicTrade.{sym}" for sym in SYMBOLS]
        for i in range(0, len(args), 10):
            await ws.send(json.dumps({"op": "subscribe", "args": args[i:i+10]}))
        print("Connected. Waiting for trades...")
        with open(LOG_PATH, "w", encoding="utf-8") as log_file:
            logged = 0
            async for message in ws:
                msg_text = message.decode("utf-8", errors="replace") if isinstance(message, bytes) else message
                try:
                    obj = json.loads(msg_text)
                except json.JSONDecodeError:
                    obj = {}
                # Respond to server pings
                if obj.get("op") == "ping" or obj.get("type") == "ping":
                    await ws.send(json.dumps({"op": "pong"}))
                    continue
                print(msg_text)
                if logged < 50:
                    log_file.write(msg_text + "\n")
                    log_file.flush()
                    logged += 1
                if logged >= 50:
                    print(f"Logged 50 messages to {LOG_PATH} — done.")
                    break

if __name__ == "__main__":
    asyncio.run(main())
