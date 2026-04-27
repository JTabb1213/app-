#!/usr/bin/env python3
"""
Gate.io WebSocket ticker test.

Subscribes to the spot.tickers channel for all USDT pairs in data/coin_aliases.json
and logs the first 50 messages.
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
        sym = entry.get("exchange_symbols", {}).get("gateio")
        if sym:
            pairs.append(f"{sym}_USDT")
    return sorted(pairs)


async def subscribe_gateio(ws, pairs, channel):
    await ws.send(json.dumps({
        "time": int(time.time()),
        "channel": channel,
        "event": "subscribe",
        "payload": pairs,
    }))


async def main() -> None:
    pairs = list(load_pairs())
    print(f"Connecting to Gate.io with {len(pairs)} USDT ticker pairs")
    print(f"Logging first 50 messages to {LOG_PATH}")
    last_ping = time.time()
    async with websockets.connect("wss://api.gateio.ws/ws/v4/", ping_interval=None) as ws:
        await subscribe_gateio(ws, pairs, "spot.tickers")
        print("Connected. Waiting for tickers...")
        with open(LOG_PATH, "w", encoding="utf-8") as log_file:
            logged = 0
            async for message in ws:
                if time.time() - last_ping >= 10:
                    await ws.send(json.dumps({"time": int(time.time()), "channel": "spot.ping"}))
                    last_ping = time.time()
                msg_text = message.decode("utf-8", errors="replace") if isinstance(message, bytes) else message
                try:
                    obj = json.loads(msg_text)
                    if (obj.get("event") == "subscribe" and
                            obj.get("result", {}).get("status") == "fail"):
                        err_msg = obj.get("error", {}).get("message", "")
                        bad = err_msg.replace("unknown currency pair: ", "").strip()
                        if bad and bad in pairs:
                            pairs.remove(bad)
                            print(f"[gateio] Removed unknown pair '{bad}', resubscribing")
                            await subscribe_gateio(ws, pairs, "spot.tickers")
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

# END
