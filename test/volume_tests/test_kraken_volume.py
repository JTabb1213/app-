#!/usr/bin/env python3
"""
Kraken raw trade-volume subscription test.

Subscribes to Kraken's trade channel for all USD pairs from
data/coin_aliases.json and logs the first 50 raw messages.
"""

import asyncio
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from volume_symbols import kraken_pairs

try:
    import websockets
except ImportError:
    print("ERROR: 'websockets' package not found. Run: pip install websockets")
    raise SystemExit(1)

WS_URL = "wss://ws.kraken.com/v2"
PAIRS = kraken_pairs()
LOG_PATH = ROOT / f"{pathlib.Path(__file__).stem}.log"

async def main() -> None:
    print(f"Connecting to Kraken with {len(PAIRS)} USD pairs")
    print(f"Logging first 50 messages to {LOG_PATH}")
    async with websockets.connect(WS_URL, ping_interval=30) as ws:
        await ws.send(json.dumps({
            "method": "subscribe",
            "params": {"channel": "trade", "symbol": PAIRS},
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
