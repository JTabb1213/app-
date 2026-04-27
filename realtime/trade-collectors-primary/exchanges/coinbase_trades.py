"""
Coinbase trade connector.

Subscribes to the "matches" channel (individual trade executions).

Match fields:
  price    — execution price
  size     — quantity
  side     — "buy" or "sell" (taker side)
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


class CoinbaseTradeConnector(BaseExchange):
    NAME = "coinbase"

    def __init__(self, producer: StreamProducer):
        super().__init__(producer)
        self._ws_url = config.COINBASE_WS_URL

    def _load_products(self) -> List[str]:
        try:
            with open(config.ALIAS_JSON_PATH) as fp:
                alias_data = json.load(fp)
            products = []
            for entry in alias_data.get("assets", {}).values():
                sym = entry.get("exchange_symbols", {}).get("coinbase")
                if sym:
                    products.append(f"{sym}-USD")
            products = sorted(set(products))
            logger.info(f"[coinbase-trades] Loaded {len(products)} products")
            return products
        except Exception as e:
            logger.warning(f"[coinbase-trades] Failed to load products: {e}")
            return ["BTC-USD", "ETH-USD", "SOL-USD"]

    async def _connect_and_stream(self) -> None:
        products = self._load_products()
        if not products:
            logger.warning("[coinbase-trades] No products — sleeping 30s")
            await asyncio.sleep(30)
            return

        logger.info(f"[coinbase-trades] Subscribing to {len(products)} products")

        async with websockets.connect(self._ws_url, ping_interval=30) as ws:
            await ws.send(json.dumps({
                "type": "subscribe",
                "product_ids": products,
                "channels": ["matches"],
            }))
            logger.info("[coinbase-trades] Connected and subscribed")

            async for message in ws:
                data = json.loads(message)
                if data.get("type") not in ("match", "last_match"):
                    continue

                try:
                    price = float(data["price"])
                    size = float(data["size"])
                    side = data.get("side", "unknown")
                except (KeyError, ValueError, TypeError):
                    continue

                tick = RawTick(
                    exchange="coinbase",
                    pair=data.get("product_id", ""),
                    data={
                        "price": price,
                        "size": size,
                        "side": side,
                        "type": "trade",
                    },
                    received_at=time.time(),
                )
                await self._emit(tick)
