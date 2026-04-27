#!/usr/bin/env python3
"""
Gate.io raw trade-volume subscription test.

Subscribes to Gate.io spot.trades for all USDT pairs from
data/coin_aliases.json and logs the first 50 raw messages.
"""

import asyncio
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from volume_symbols import gateio_pairs

try:
    import websockets
except ImportError:
    print("ERROR: 'websockets' package not found. Run: pip install websockets")
    raise SystemExit(1)

WS_URL = "wss://api.gateio.ws/ws/v4/"
PAIRS = gateio_pairs()
LOG_PATH = ROOT / f"{pathlib.Path(__file__).stem}.log"

async def subscribe(ws, pairs):
    await ws.send(json.dumps({
        "time": int(time.time()),
        "channel": "spot.trades",
        "event": "subscribe",
        "payload": pairs,
    }))


async def main() -> None:
    pairs = list(PAIRS)
    print(f"Connecting to Gate.io with {len(pairs)} USDT pairs")
    print(f"Logging first 50 messages to {LOG_PATH}")
    last_ping = time.time()
    async with websockets.connect(WS_URL, ping_interval=None) as ws:
        await subscribe(ws, pairs)
        print("Connected. Waiting for trades...")
        with open(LOG_PATH, "w", encoding="utf-8") as log_file:
            logged = 0
            async for message in ws:
                if time.time() - last_ping >= 10:
                    await ws.send(json.dumps({"time": int(time.time()), "channel": "spot.ping"}))
                    last_ping = time.time()
                msg_text = message.decode("utf-8", errors="replace") if isinstance(message, bytes) else message
                # Detect unknown-pair error and resubscribe without the bad pair
                try:
                    obj = json.loads(msg_text)
                    if (obj.get("event") == "subscribe" and
                            obj.get("result", {}).get("status") == "fail"):
                        err_msg = obj.get("error", {}).get("message", "")
                        # Extract "unknown currency pair: XYZ_USDT"
                        bad = err_msg.replace("unknown currency pair: ", "").strip()
                        if bad and bad in pairs:
                            pairs.remove(bad)
                            print(f"[gateio] Removed unknown pair '{bad}', resubscribing {len(pairs)} pairs")
                            await subscribe(ws, pairs)
                        continue
                except (json.JSONDecodeError, AttributeError):
                    pass
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

