#!/usr/bin/env python3
"""
Kraken WebSocket v2 ticker test.

Subscribes to the ticker channel for all USD pairs in data/coin_aliases.json
and logs the first 50 messages.
"""

import asyncio
import json
import pathlib

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
        sym = entry.get("exchange_symbols", {}).get("kraken")
        if sym:
            pairs.append(f"{sym}/USD")
    return sorted(pairs)


async def main() -> None:
    pairs = load_pairs()
    print(f"Connecting to Kraken with {len(pairs)} USD ticker pairs")
    print(f"Logging first 50 messages to {LOG_PATH}")
    async with websockets.connect("wss://ws.kraken.com/v2", ping_interval=30) as ws:
        await ws.send(json.dumps({
            "method": "subscribe",
            "params": {"channel": "ticker", "symbol": pairs},
        }))
        print("Connected. Waiting for tickers...")
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

# END
