#!/usr/bin/env python3
"""
OKX raw trade-volume subscription test.

Subscribes to OKX trades channel for all USDT pairs from
data/coin_aliases.json and logs the first 50 raw messages.
"""

import asyncio
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from volume_symbols import okx_pairs

try:
    import websockets
except ImportError:
    print("ERROR: 'websockets' package not found. Run: pip install websockets")
    raise SystemExit(1)

WS_URL = "wss://ws.okx.com:8443/ws/v5/public"
PAIRS = okx_pairs()
LOG_PATH = ROOT / f"{pathlib.Path(__file__).stem}.log"

async def main() -> None:
    print(f"Connecting to OKX with {len(PAIRS)} USDT pairs")
    print(f"Logging first 50 messages to {LOG_PATH}")
    async with websockets.connect(WS_URL, ping_interval=20) as ws:
        await ws.send(json.dumps({
            "op": "subscribe",
            "args": [{"channel": "trades", "instId": pair} for pair in PAIRS],
        }))
        print("Connected. Waiting for trades...")
        with open(LOG_PATH, "w", encoding="utf-8") as log_file:
            logged = 0
            async for message in ws:
                msg_text = message.decode("utf-8", errors="replace") if isinstance(message, bytes) else message
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
