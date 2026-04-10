"""
MEXC websocket connector.

Connects to MEXC's WebSocket API, subscribes to the bookTicker stream,
and emits RawTick events to the stream.

Docs: https://mexcdevelop.github.io/apidocs/spot_v3_en/

MEXC specifics:
  - Pair format: "BTCUSDT" (concatenated, like Binance)
  - bookTicker stream gives: bid (b), ask (a) — no last price or volume
  - PING/PONG via {"method": "PING"}
  - ⚠️ Blocks US IPs — deploy outside the US

Note: bookTicker only provides bid/ask. The ingestor's normalizer
will compute mid price from bid/ask as the price.
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


class MexcConnector(BaseExchange):
    NAME = "mexc"

    def __init__(
        self,
        producer: StreamProducer,
        quote_currencies: Optional[List[str]] = None,
    ):
        super().__init__(producer)
        self._ws_url = config.MEXC_WS_URL
        self._rest_url = config.MEXC_REST_URL
        self._quote_currencies = quote_currencies or config.QUOTE_CURRENCIES
        self._symbols: List[str] = []

    # -- Symbol discovery ---------------------------------------------------

    def _load_symbols_from_json(self) -> List[str]:
        """Build MEXC symbols from coin_aliases.json standard symbols."""
        try:
            with open(config.ALIAS_JSON_PATH) as fp:
                alias_data = json.load(fp)
            symbols = []
            for entry in alias_data.get("assets", {}).values():
                symbol = entry.get("symbol", "")
                if symbol:
                    for quote in self._quote_currencies:
                        symbols.append(f"{symbol}{quote}")
            symbols = sorted(set(symbols))
            if symbols:
                logger.info(f"[mexc] Built {len(symbols)} symbols from coin_aliases.json")
                return symbols
        except Exception as e:
            logger.warning(f"[mexc] Failed to load symbols from JSON: {e}")
        return []

    async def _fetch_symbols_from_api(self) -> List[str]:
        """Fetch available symbols from MEXC REST API."""
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
                if quote.upper() in self._quote_currencies and status == "ENABLED":
                    symbols.append(symbol)
            symbols = sorted(set(symbols))
            logger.info(f"[mexc] Fetched {len(symbols)} symbols from API (fallback)")
            return symbols
        except Exception as e:
            logger.error(f"[mexc] API fallback failed: {e}")
            return []

    async def _fetch_symbols(self) -> List[str]:
        symbols = self._load_symbols_from_json()
        if symbols:
            return symbols
        symbols = await self._fetch_symbols_from_api()
        if symbols:
            return symbols
        logger.warning("[mexc] Using hardcoded seed symbols (last resort)")
        return ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
                "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT"]

    # -- WebSocket streaming ------------------------------------------------

    async def _connect_and_stream(self) -> None:
        self._symbols = await self._fetch_symbols()

        if not self._symbols:
            logger.warning("[mexc] No symbols — sleeping 30s")
            await asyncio.sleep(30)
            return

        logger.info(f"[mexc] Subscribing to {len(self._symbols)} symbols")

        async with websockets.connect(self._ws_url, ping_interval=None) as ws:
            # Subscribe to bookTicker for each symbol
            params = [f"spot@public.bookTicker.v3.api@{sym}" for sym in self._symbols]
            await ws.send(json.dumps({"method": "SUBSCRIPTION", "params": params}))
            logger.info("[mexc] Subscribed to bookTicker streams")

            last_ping = time.time()

            async for message in ws:
                # Send keepalive PING every 30 seconds
                if time.time() - last_ping >= 30:
                    await ws.send(json.dumps({"method": "PING"}))
                    last_ping = time.time()

                data = json.loads(message)

                # Skip ACK / PONG messages
                if "code" in data:
                    continue

                d = data.get("d", {})
                symbol = d.get("s", "")
                if not symbol:
                    continue

                try:
                    bid = float(d.get("b", 0) or 0)
                    ask = float(d.get("a", 0) or 0)
                except (ValueError, TypeError):
                    continue

                # bookTicker doesn't provide last price or volume
                tick = RawTick(
                    exchange="mexc",
                    pair=symbol,
                    data={
                        "bid": bid, "ask": ask, "last": 0,
                        "vwap": None, "volume_24h": None,
                    },
                    received_at=time.time(),
                )
                await self._emit(tick)
