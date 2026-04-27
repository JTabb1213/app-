"""
Bybit websocket connector.

Connects to Bybit's V5 WebSocket API, subscribes to the tickers stream
for spot USDT pairs, and emits RawTick events to the stream.

Docs: https://bybit-exchange.github.io/docs/v5/websocket/public/ticker

Bybit specifics:
  - Pair format: "BTCUSDT" (concatenated, no separator)
  - Subscribe topic: "tickers.<symbol>"  e.g. "tickers.BTCUSDT"
  - Response fields: bid1Price, ask1Price, lastPrice, volume24h
  - Server sends ping every 20s; client must reply with pong
  - Max 10 topics per subscribe message; we batch accordingly
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

BYBIT_BATCH_SIZE = 10  # max topics per subscribe message


class BybitConnector(BaseExchange):
    NAME = "bybit"

    def __init__(
        self,
        producer: StreamProducer,
        quote_currencies: Optional[List[str]] = None,
    ):
        super().__init__(producer)
        self._ws_url = config.BYBIT_WS_URL
        self._rest_url = config.BYBIT_REST_URL
        self._quote_currencies = quote_currencies or config.QUOTE_CURRENCIES
        self._symbols: List[str] = []

    # -- Symbol discovery ---------------------------------------------------

    def _load_symbols_from_json(self) -> List[str]:
        """Build Bybit symbols from coin_aliases.json standard symbols."""
        try:
            with open(config.ALIAS_JSON_PATH) as fp:
                alias_data = json.load(fp)
            symbols = []
            for entry in alias_data.get("assets", {}).values():
                symbol = entry.get("symbol", "")
                if symbol:
                    for quote in self._quote_currencies:
                        sym = f"{symbol}{quote}"
                        # Skip self-referencing pairs
                        if symbol.upper() != quote.upper():
                            symbols.append(sym)
            symbols = sorted(set(symbols))
            if symbols:
                logger.info(f"[bybit] Built {len(symbols)} symbols from coin_aliases.json")
                return symbols
        except Exception as e:
            logger.warning(f"[bybit] Failed to load symbols from JSON: {e}")
        return []

    async def _fetch_symbols_from_api(self) -> List[str]:
        """Fetch available spot instruments from Bybit REST API."""
        try:
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=10)
                async with session.get(self._rest_url, timeout=timeout) as resp:
                    data = await resp.json()
            symbols = []
            for item in data.get("result", {}).get("list", []):
                symbol = item.get("symbol", "")       # e.g. "BTCUSDT"
                quote = item.get("quoteCoin", "")      # e.g. "USDT"
                status = item.get("status", "")
                if quote.upper() in self._quote_currencies and status == "Trading":
                    symbols.append(symbol)
            symbols = sorted(set(symbols))
            logger.info(f"[bybit] Fetched {len(symbols)} symbols from API (fallback)")
            return symbols
        except Exception as e:
            logger.error(f"[bybit] API fallback failed: {e}")
            return []

    async def _fetch_symbols(self) -> List[str]:
        symbols = self._load_symbols_from_json()
        if symbols:
            return symbols
        symbols = await self._fetch_symbols_from_api()
        if symbols:
            return symbols
        logger.warning("[bybit] Using hardcoded seed symbols (last resort)")
        return ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
                "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT"]

    # -- WebSocket streaming ------------------------------------------------

    async def _connect_and_stream(self) -> None:
        self._symbols = await self._fetch_symbols()

        if not self._symbols:
            logger.warning("[bybit] No symbols — sleeping 30s")
            await asyncio.sleep(30)
            return

        topics = [f"tickers.{sym}" for sym in self._symbols]
        logger.info(f"[bybit] Subscribing to {len(topics)} ticker topics")

        async with websockets.connect(self._ws_url, ping_interval=20) as ws:
            # Bybit limits 10 topics per subscribe message
            for i in range(0, len(topics), BYBIT_BATCH_SIZE):
                batch = topics[i: i + BYBIT_BATCH_SIZE]
                await ws.send(json.dumps({
                    "op": "subscribe",
                    "args": batch,
                }))
                await asyncio.sleep(0.1)

            logger.info(f"[bybit] Sent subscribe messages for {len(topics)} topics")

            async for message in ws:
                data = json.loads(message)

                # Server ping → reply pong
                if data.get("op") == "ping":
                    await ws.send(json.dumps({"op": "pong"}))
                    continue

                # Skip subscribe acks
                if "success" in data or "op" in data:
                    continue

                topic = data.get("topic", "")
                if not topic.startswith("tickers."):
                    continue

                item = data.get("data", {})
                if not item:
                    continue

                symbol = topic[len("tickers."):]
                try:
                    bid = float(item.get("bid1Price", 0) or 0)
                    ask = float(item.get("ask1Price", 0) or 0)
                    last = float(item.get("lastPrice", 0) or 0)
                    volume = float(item.get("volume24h", 0) or 0)
                except (ValueError, TypeError):
                    continue

                tick = RawTick(
                    exchange="bybit",
                    pair=symbol,
                    data={
                        "bid": bid, "ask": ask, "last": last,
                        "vwap": None, "volume_24h": volume,
                    },
                    received_at=time.time(),
                )
                await self._emit(tick)
