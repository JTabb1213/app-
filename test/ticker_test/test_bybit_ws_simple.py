#!/usr/bin/env python3
"""
Bybit WebSocket ticker test.

Subscribes to the tickers channel for all USDT spot pairs in data/coin_aliases.json
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


def load_symbols() -> list[str]:
    with open(COIN_ALIASES_PATH, "r", encoding="utf-8") as f:
        assets = json.load(f)["assets"]
    symbols = []
    for entry in assets.values():
        sym = entry.get("exchange_symbols", {}).get("bybit")
        if sym:
            symbols.append(f"{sym}USDT")
    return sorted(symbols)


async def main() -> None:
    symbols = load_symbols()
    print(f"Connecting to Bybit with {len(symbols)} USDT ticker pairs")
    print(f"Logging first 50 messages to {LOG_PATH}")
    async with websockets.connect("wss://stream.bybit.com/v5/public/spot", ping_interval=20) as ws:
        # Bybit limits to 10 args per subscribe message
        args = [f"tickers.{sym}" for sym in symbols]
        for i in range(0, len(args), 10):
            await ws.send(json.dumps({"op": "subscribe", "args": args[i:i+10]}))
        print("Connected. Waiting for tickers...")
        with open(LOG_PATH, "w", encoding="utf-8") as log_file:
            logged = 0
            async for message in ws:
                msg_text = message.decode("utf-8", errors="replace") if isinstance(message, bytes) else message
                try:
                    obj = json.loads(msg_text)
                except json.JSONDecodeError:
                    obj = {}
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
