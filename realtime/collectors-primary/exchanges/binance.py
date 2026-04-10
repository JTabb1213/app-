"""
Binance.US websocket connector.

Connects to Binance's WebSocket API, subscribes to the ticker stream
for USDT pairs, and emits RawTick events to the stream.
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


TEST_SYMBOLS_OVERRIDE = None


class BinanceConnector(BaseExchange):
    NAME = "binance"

    def __init__(
        self,
        producer: StreamProducer,
        quote_currencies: Optional[List[str]] = None,
    ):
        super().__init__(producer)
        self._ws_base_url = config.BINANCE_WS_URL
        self._rest_url = config.BINANCE_REST_URL
        self._quote_currencies = quote_currencies or ["USDT"]
        self._symbols: List[str] = []

    # -- Symbol discovery ---------------------------------------------------

    def _load_symbols_from_json(self) -> List[str]:
        try:
            with open(config.ALIAS_JSON_PATH) as fp:
                alias_data = json.load(fp)
            symbols = []
            for entry in alias_data.get("assets", {}).values():
                binance_sym = entry.get("exchange_symbols", {}).get("binance")
                if binance_sym:
                    symbols.append(f"{binance_sym.lower()}usdt")
            symbols = sorted(set(symbols))
            if symbols:
                logger.info(f"[binance] Loaded {len(symbols)} symbols from coin_aliases.json")
                return symbols
        except Exception as e:
            logger.warning(f"[binance] Failed to load symbols from JSON: {e}")
        return []

    async def _fetch_symbols_from_api(self) -> List[str]:
        try:
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=10)
                async with session.get(self._rest_url, timeout=timeout) as resp:
                    data = await resp.json()
            symbols = []
            for item in data.get("symbols", []):
                symbol = item.get("symbol", "")
                quote = item.get("quoteAsset", "")
                status = item.get("status", "")
                if quote.upper() in self._quote_currencies and status == "TRADING":
                    symbols.append(symbol.lower())
            symbols = sorted(set(symbols))
            logger.info(f"[binance] Fetched {len(symbols)} symbols from API (fallback)")
            return symbols
        except Exception as e:
            logger.error(f"[binance] API fallback failed: {e}")
            return []

    async def _fetch_symbols(self) -> List[str]:
        symbols = self._load_symbols_from_json()
        if symbols:
            return symbols
        symbols = await self._fetch_symbols_from_api()
        if symbols:
            return symbols
        logger.warning("[binance] Using hardcoded seed symbols (last resort)")
        return ["btcusdt", "ethusdt", "solusdt", "xrpusdt", "adausdt",
                "dogeusdt", "avaxusdt", "dotusdt", "linkusdt", "ltcusdt"]

    # -- WebSocket streaming ------------------------------------------------

    async def _connect_and_stream(self) -> None:
        self._symbols = await self._fetch_symbols()

        if TEST_SYMBOLS_OVERRIDE is not None:
            self._symbols = TEST_SYMBOLS_OVERRIDE
            logger.info(f"[binance] ⚠️  TEST MODE: {len(self._symbols)} symbols")

        if not self._symbols:
            logger.warning("[binance] No symbols — sleeping 30s")
            await asyncio.sleep(30)
            return

        streams = "/".join(f"{sym}@ticker" for sym in self._symbols)
        ws_url = f"{self._ws_base_url}/stream?streams={streams}"

        logger.info(f"[binance] Subscribing to {len(self._symbols)} symbols")

        async with websockets.connect(ws_url, ping_interval=30) as ws:
            logger.info("[binance] Connected to WebSocket")

            async for message in ws:
                data = json.loads(message)
                ticker = data.get("data", data)
                if ticker.get("e") != "24hrTicker":
                    continue

                symbol = ticker.get("s", "")
                try:
                    bid = float(ticker.get("b", 0) or 0)
                    ask = float(ticker.get("a", 0) or 0)
                    last = float(ticker.get("c", 0) or 0)
                    volume = float(ticker.get("v", 0) or 0)
                except (ValueError, TypeError):
                    continue

                tick = RawTick(
                    exchange="binance",
                    pair=symbol,
                    data={
                        "bid": bid, "ask": ask, "last": last,
                        "vwap": None, "volume_24h": volume,
                    },
                    received_at=time.time(),
                )
                await self._emit(tick)
