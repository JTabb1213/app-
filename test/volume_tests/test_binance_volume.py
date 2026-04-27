#!/usr/bin/env python3
"""
Binance.US raw trade-volume subscription test.

Subscribes to Binance.US combined trade streams for all USDT pairs from
data/coin_aliases.json and logs the first 50 raw messages.
"""

import asyncio
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from volume_symbols import binance_symbols

try:
    import websockets
except ImportError:
    print("ERROR: 'websockets' package not found. Run: pip install websockets")
    raise SystemExit(1)

SYMBOLS = binance_symbols()
WS_URL = "wss://stream.binance.us:9443/stream?streams=" + "/".join(f"{sym.lower()}@trade" for sym in SYMBOLS)
LOG_PATH = ROOT / f"{pathlib.Path(__file__).stem}.log"

async def main() -> None:
    print(f"Connecting to Binance.US with {len(SYMBOLS)} USDT pairs")
    print(f"Logging up to 20 messages (or 3 min timeout) to {LOG_PATH}")
    deadline = time.time() + 180
    async with websockets.connect(WS_URL, ping_interval=20) as ws:
        print("Connected. Waiting for trades...")
        with open(LOG_PATH, "w", encoding="utf-8") as log_file:
            logged = 0
            async for message in ws:
                if time.time() > deadline:
                    print(f"Timeout — logged {logged} messages to {LOG_PATH}.")
                    break
                msg_text = message.decode("utf-8", errors="replace") if isinstance(message, bytes) else message
                print(msg_text)
                if logged < 20:
                    log_file.write(msg_text + "\n")
                    log_file.flush()
                    logged += 1
                if logged >= 20:
                    print(f"Logged 20 messages to {LOG_PATH} — done.")
                    break

if __name__ == "__main__":
    asyncio.run(main())
