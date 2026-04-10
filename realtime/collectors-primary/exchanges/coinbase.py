"""
Coinbase websocket connector.

Connects to Coinbase's WebSocket feed API, subscribes to the ticker channel
for USD pairs, and emits RawTick events to the stream.
"""

import asyncio
import json
import logging
import time
from typing import List, Optional

import aiohttp
import websockets

import config
from shared.models import RawTick
from shared.exchanges.base import BaseExchange
from shared.stream.producer import StreamProducer

logger = logging.getLogger(__name__)


TEST_PRODUCTS_OVERRIDE = None


class CoinbaseConnector(BaseExchange):
    NAME = "coinbase"

    def __init__(
        self,
        producer: StreamProducer,
        quote_currencies: Optional[List[str]] = None,
    ):
        super().__init__(producer)
        self._ws_url = config.COINBASE_WS_URL
        self._rest_url = config.COINBASE_REST_URL
        self._quote_currencies = quote_currencies or config.QUOTE_CURRENCIES
        self._products: List[str] = []

    # -- Symbol discovery ---------------------------------------------------

    def _load_products_from_json(self) -> List[str]:
        try:
            with open(config.ALIAS_JSON_PATH) as fp:
                alias_data = json.load(fp)
            products = []
            for entry in alias_data.get("assets", {}).values():
                coinbase_sym = entry.get("exchange_symbols", {}).get("coinbase")
                if coinbase_sym:
                    products.append(f"{coinbase_sym}-USD")
            products = sorted(set(products))
            if products:
                logger.info(f"[coinbase] Loaded {len(products)} products from coin_aliases.json")
                return products
        except Exception as e:
            logger.warning(f"[coinbase] Failed to load products from JSON: {e}")
        return []

    async def _fetch_products_from_api(self) -> List[str]:
        try:
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=10)
                async with session.get(self._rest_url, timeout=timeout) as resp:
                    data = await resp.json()
            products = []
            for product in data:
                product_id = product.get("id", "")
                quote = product.get("quote_currency", "")
                status = product.get("status", "")
                if quote.upper() in self._quote_currencies and status == "online":
                    products.append(product_id)
            products = sorted(set(products))
            logger.info(f"[coinbase] Fetched {len(products)} products from API (fallback)")
            return products
        except Exception as e:
            logger.error(f"[coinbase] API fallback failed: {e}")
            return []

    async def _fetch_products(self) -> List[str]:
        products = self._load_products_from_json()
        if products:
            return products
        products = await self._fetch_products_from_api()
        if products:
            return products
        logger.warning("[coinbase] Using hardcoded seed products (last resort)")
        return ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD",
                "DOGE-USD", "AVAX-USD", "DOT-USD", "LINK-USD", "LTC-USD"]

    # -- WebSocket streaming ------------------------------------------------

    async def _connect_and_stream(self) -> None:
        self._products = await self._fetch_products()

        if TEST_PRODUCTS_OVERRIDE is not None:
            self._products = TEST_PRODUCTS_OVERRIDE
            logger.info(f"[coinbase] ⚠️  TEST MODE: {len(self._products)} products")

        if not self._products:
            logger.warning("[coinbase] No products — sleeping 30s")
            await asyncio.sleep(30)
            return

        logger.info(f"[coinbase] Subscribing to {len(self._products)} products")

        subscribe_msg = json.dumps({
            "type": "subscribe",
            "product_ids": self._products,
            "channels": ["ticker"],
        })

        async with websockets.connect(self._ws_url, ping_interval=30) as ws:
            await ws.send(subscribe_msg)
            logger.info("[coinbase] Subscribed to ticker channel")

            async for message in ws:
                data = json.loads(message)
                if data.get("type") != "ticker":
                    continue

                product_id = data.get("product_id", "")
                try:
                    bid = float(data.get("best_bid", 0) or 0)
                    ask = float(data.get("best_ask", 0) or 0)
                    last = float(data.get("price", 0) or 0)
                    volume = float(data.get("volume_24h", 0) or 0)
                except (ValueError, TypeError):
                    continue

                tick = RawTick(
                    exchange="coinbase",
                    pair=product_id,
                    data={
                        "bid": bid, "ask": ask, "last": last,
                        "vwap": None, "volume_24h": volume,
                    },
                    received_at=time.time(),
                )
                await self._emit(tick)
