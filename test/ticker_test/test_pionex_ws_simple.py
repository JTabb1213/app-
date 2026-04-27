#!/usr/bin/env python3
"""
Pionex WebSocket trade/ticker test.

Pionex's public stream only supports TRADE and DEPTH topics (no TICKER).
Subscribes to TRADE for all USDT pairs in data/coin_aliases.json and logs
the first 50 messages.
"""

import asyncio
import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
COIN_ALIASES_PATH = ROOT / "data" / "coin_aliases.json"
LOG_PATH = pathlib.Path(__file__).parent / f"{pathlib.Path(__file__).stem}.log"

try:
    import websockets
except ImportError:
    print("ERROR: 'websockets' package not found. Run: pip install websockets")
    raise SystemExit(1)


def load_pairs() -> list[str]:
    with open(COIN_ALIASES_PATH, "r", encoding="utf-8") as f:
        assets = json.load(f)["assets"]
    pairs = []
    for entry in assets.values():
        sym = entry.get("exchange_symbols", {}).get("pionex")
        if sym:
            pairs.append(f"{sym}_USDT")
    return sorted(pairs)


async def main() -> None:
    pairs = load_pairs()
    print(f"Connecting to Pionex with {len(pairs)} USDT trade pairs")
    print(f"Logging first 50 messages to {LOG_PATH}")
    async with websockets.connect("wss://ws.pionex.com/wsPub", ping_interval=None) as ws:
        for pair in pairs:
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

# END
