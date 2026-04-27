#!/usr/bin/env python3
"""
MEXC raw trade-volume subscription test.

Subscribes to a MEXC public deal/trade stream for a few sample symbols and
prints raw websocket messages.
"""

import asyncio
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from volume_symbols import mexc_symbols

try:
    import websockets
except ImportError:
    print("ERROR: 'websockets' package not found. Run: pip install websockets")
    raise SystemExit(1)

WS_URL = "wss://wbs.mexc.com/ws"
SYMBOLS = mexc_symbols()
PING_INTERVAL = 30
LOG_PATH = ROOT / f"{pathlib.Path(__file__).stem}.log"

async def main() -> None:
    print(f"Connecting to MEXC: {WS_URL}")
    async with websockets.connect(WS_URL, ping_interval=None) as ws:
        params = [f"spot@public.deals.v3.api@{symbol}" for symbol in SYMBOLS]
        await ws.send(json.dumps({"method": "SUBSCRIPTION", "params": params}))
        print("Subscribed to MEXC deal streams for:", SYMBOLS)

        last_ping = time.time()
        with open(LOG_PATH, "w", encoding="utf-8") as log_file:
            logged = 0
            async for message in ws:
                now = time.time()
                if now - last_ping >= PING_INTERVAL:
                    await ws.send(json.dumps({"method": "PING"}))
                    last_ping = now
                if logged < 50:
                    msg_text = message.decode("utf-8", errors="replace") if isinstance(message, bytes) else message
                    log_file.write(msg_text + "\n")
                    log_file.flush()
                    logged += 1
                print(message)


if __name__ == "__main__":
    asyncio.run(main())
