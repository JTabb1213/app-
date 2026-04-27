"""
Bybit trade connector.

Subscribes to the "publicTrade.*" topic on Bybit's spot WebSocket
for individual trade executions.

Trade data fields:
  p  — price
  v  — volume (quantity in base asset)
  S  — side: "Buy" or "Sell"
"""

import asyncio
import json
import logging
import time
from typing import List

import websockets

import config
from shared.models import RawTick
from shared.exchanges.base import BaseExchange
from shared.stream.producer import StreamProducer

logger = logging.getLogger(__name__)

# Bybit enforces a max of 10 topics per subscribe message
BYBIT_BATCH_SIZE = 10


class BybitTradeConnector(BaseExchange):
    NAME = "bybit"

    def __init__(self, producer: StreamProducer):
        super().__init__(producer)
        self._ws_url = config.BYBIT_WS_URL

    def _load_symbols(self) -> List[str]:
        """Load USDT spot symbols from coin_aliases.json."""
        try:
            with open(config.ALIAS_JSON_PATH) as fp:
                alias_data = json.load(fp)
            symbols = []
            for entry in alias_data.get("assets", {}).values():
                sym = entry.get("exchange_symbols", {}).get("bybit")
                if sym:
                    symbols.append(f"{sym}USDT")  # e.g. ETHUSDT
            symbols = sorted(set(symbols))
            logger.info(f"[bybit-trades] Loaded {len(symbols)} USDT symbols")
            return symbols
        except Exception as e:
            logger.warning(f"[bybit-trades] Failed to load symbols: {e}")
            return ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    async def _connect_and_stream(self) -> None:
        symbols = self._load_symbols()
        if not symbols:
            await asyncio.sleep(30)
            return

        logger.info(f"[bybit-trades] Subscribing to {len(symbols)} symbols")

        async with websockets.connect(self._ws_url, ping_interval=20) as ws:
            # Bybit limits 10 args per subscribe message — batch them
            args = [f"publicTrade.{sym}" for sym in symbols]
            for i in range(0, len(args), BYBIT_BATCH_SIZE):
                await ws.send(json.dumps({
                    "op": "subscribe",
                    "args": args[i:i + BYBIT_BATCH_SIZE],
                }))

            logger.info("[bybit-trades] Connected and subscribed")

            async for message in ws:
                data = json.loads(message)

                # Respond to server pings
                if data.get("op") == "ping":
                    await ws.send(json.dumps({"op": "pong"}))
                    continue

                if data.get("topic", "").startswith("publicTrade."):
                    for item in data.get("data", []):
                        try:
                            price = float(item["p"])
                            size = float(item["v"])   # base asset quantity
                            side = item.get("S", "Buy").lower()  # "Buy" / "Sell"
                        except (KeyError, ValueError, TypeError):
                            continue

                        tick = RawTick(
                            exchange="bybit",
                            pair=item.get("s", ""),
                            data={
                                "price": price,
                                "size": size,
                                "side": side,
                                "type": "trade",
                            },
                            received_at=time.time(),
                        )
                        await self._emit(tick)
