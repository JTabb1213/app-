"""
Binance.US trade connector.

Subscribes to @trade streams (individual trade executions) for all
coins in coin_aliases.json.  Emits RawTick with side information.

Trade stream fields:
  p  — price
  q  — quantity
  m  — isBuyerMaker (true = sell, false = buy from taker perspective)
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


class BinanceTradeConnector(BaseExchange):
    NAME = "binance"

    def __init__(self, producer: StreamProducer):
        super().__init__(producer)
        self._ws_base_url = config.BINANCE_WS_URL

    def _load_symbols(self) -> List[str]:
        """Load symbols from coin_aliases.json — USDT pairs only."""
        try:
            with open(config.ALIAS_JSON_PATH) as fp:
                alias_data = json.load(fp)
            symbols = []
            for entry in alias_data.get("assets", {}).values():
                sym = entry.get("exchange_symbols", {}).get("binance")
                if sym:
                    symbols.append(sym.lower() + "usdt")  # e.g. ethusdt
            symbols = sorted(set(symbols))
            logger.info(f"[binance-trades] Loaded {len(symbols)} USDT symbols")
            return symbols
        except Exception as e:
            logger.warning(f"[binance-trades] Failed to load symbols: {e}")
            return ["btcusdt", "ethusdt", "solusdt"]

    async def _connect_and_stream(self) -> None:
        symbols = self._load_symbols()
        if not symbols:
            logger.warning("[binance-trades] No symbols — sleeping 30s")
            await asyncio.sleep(30)
            return

        # Binance combined stream requires lowercase
        streams = "/".join(f"{sym}@trade" for sym in symbols)
        ws_url = f"{self._ws_base_url}/stream?streams={streams}"

        logger.info(f"[binance-trades] Subscribing to {len(symbols)} trade streams")

        async with websockets.connect(ws_url, ping_interval=30) as ws:
            logger.info("[binance-trades] Connected")

            async for message in ws:
                data = json.loads(message)
                trade = data.get("data", data)

                if trade.get("e") != "trade":
                    continue

                try:
                    price = float(trade["p"])
                    qty = float(trade["q"])
                    # m=true means buyer is maker → taker sold → "sell"
                    side = "sell" if trade.get("m", False) else "buy"
                except (KeyError, ValueError, TypeError):
                    continue

                tick = RawTick(
                    exchange="binance",
                    pair=trade.get("s", ""),
                    data={
                        "price": price,
                        "size": qty,
                        "side": side,
                        "type": "trade",
                    },
                    received_at=time.time(),
                )
                await self._emit(tick)
