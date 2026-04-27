#!/usr/bin/env python3
"""
Pionex raw trade-volume subscription test.

Subscribes to the Pionex TRADE topic for all USDT pairs from
data/coin_aliases.json and logs the first 50 raw messages.
"""

import asyncio
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from volume_symbols import pionex_pairs

try:
    import websockets
except ImportError:
    print("ERROR: 'websockets' package not found. Run: pip install websockets")
    raise SystemExit(1)

WS_URL = "wss://ws.pionex.com/wsPub"
PAIRS = pionex_pairs()
LOG_PATH = ROOT / f"{pathlib.Path(__file__).stem}.log"

async def main() -> None:
    print(f"Connecting to Pionex with {len(PAIRS)} USDT pairs")
    print(f"Logging first 50 messages to {LOG_PATH}")
    async with websockets.connect(WS_URL, ping_interval=None) as ws:
        for pair in PAIRS:
            await ws.send(json.dumps({"op": "SUBSCRIBE", "topic": "TRADE", "symbol": pair}))
        print("Connected. Waiting for trades...")
        with open(LOG_PATH, "w", encoding="utf-8") as log_file:
            logged = 0
            async for message in ws:
                msg_text = message.decode("utf-8", errors="replace") if isinstance(message, bytes) else message
                try:
                    obj = json.loads(msg_text)
                except json.JSONDecodeError:
                    obj = {}
                if obj.get("op") == "PING":
                    await ws.send(json.dumps({"op": "PONG", "timestamp": int(time.time() * 1000)}))
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
