"""
Kraken websocket connector.

Connects to Kraken's WebSocket v2 API, subscribes to the ticker channel
for all tradeable USD pairs, and emits RawTick events to the stream.

Ticker channel docs:
  https://docs.kraken.com/api/docs/websocket-v2/ticker
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


TEST_PAIRS_OVERRIDE = None


class KrakenConnector(BaseExchange):
    NAME = "kraken"

    def __init__(
        self,
        producer: StreamProducer,
        quote_currencies: Optional[List[str]] = None,
    ):
        super().__init__(producer)
        self._ws_url = config.KRAKEN_WS_URL
        self._rest_url = config.KRAKEN_REST_URL
        self._chunk_size = config.KRAKEN_CHUNK_SIZE
        self._quote_currencies = quote_currencies or config.QUOTE_CURRENCIES
        self._pairs: List[str] = []

    # -- Symbol discovery ---------------------------------------------------

    def _load_pairs_from_json(self) -> List[str]:
        V1_TO_V2 = {"XBT": "BTC", "XDG": "DOGE"} # known symbol overwrites
        try:
            with open(config.ALIAS_JSON_PATH) as fp:
                alias_data = json.load(fp)
            pairs = []
            for entry in alias_data.get("assets", {}).values():
                kraken_sym = entry.get("exchange_symbols", {}).get("kraken")
                if kraken_sym:
                    base = V1_TO_V2.get(kraken_sym, kraken_sym)
                    pairs.append(f"{base}/USD")
            pairs = sorted(set(pairs))
            if pairs:
                logger.info(f"[kraken] Loaded {len(pairs)} pairs from coin_aliases.json")
                return pairs
        except Exception as e:
            logger.warning(f"[kraken] Failed to load pairs from JSON: {e}")
        return []

    async def _fetch_pairs_from_api(self) -> List[str]:
        V1_TO_V2 = {"XBT": "BTC", "XDG": "DOGE"}
        try:
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=10)
                async with session.get(self._rest_url, timeout=timeout) as resp:
                    data = await resp.json()
            pairs = []
            for key, val in data.get("result", {}).items():
                wsname = val.get("wsname")
                if not wsname or ".d" in key:
                    continue
                quote = wsname.split("/")[-1] if "/" in wsname else None
                if quote and quote.upper() in self._quote_currencies:
                    pairs.append(wsname)
            translated = []
            for pair in pairs:
                parts = pair.split("/")
                if len(parts) == 2:
                    base = V1_TO_V2.get(parts[0], parts[0])
                    quote = V1_TO_V2.get(parts[1], parts[1])
                    translated.append(f"{base}/{quote}")
                else:
                    translated.append(pair)
            pairs = sorted(set(translated))
            logger.info(f"[kraken] Fetched {len(pairs)} pairs from API (fallback)")
            return pairs
        except Exception as e:
            logger.error(f"[kraken] API fallback failed: {e}")
            return []

    async def _fetch_pairs(self) -> List[str]:
        pairs = self._load_pairs_from_json()
        if pairs:
            return pairs
        pairs = await self._fetch_pairs_from_api()
        if pairs:
            return pairs
        logger.warning("[kraken] Using hardcoded seed pairs (last resort)")
        return ["BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD", "ADA/USD"]

    # -- WebSocket streaming ------------------------------------------------

    async def _connect_and_stream(self) -> None:
        self._pairs = await self._fetch_pairs()

        if TEST_PAIRS_OVERRIDE is not None:
            self._pairs = TEST_PAIRS_OVERRIDE
            logger.info(f"[kraken] ⚠️  TEST MODE: {len(self._pairs)} pairs")

        if not self._pairs:
            logger.warning("[kraken] No pairs — sleeping 30s")
            await asyncio.sleep(30)
            return

        chunks = [
            self._pairs[i : i + self._chunk_size]
            for i in range(0, len(self._pairs), self._chunk_size)
        ]

        logger.info(f"[kraken] Spawning {len(chunks)} connection(s) for {len(self._pairs)} pairs")
        await asyncio.gather(
            *[self._stream_chunk(i, chunk) for i, chunk in enumerate(chunks)]
        )

    async def _stream_chunk(self, conn_id: int, pairs: List[str]) -> None:
        subscribe_msg = json.dumps({
            "method": "subscribe",
            "params": {"channel": "ticker", "symbol": pairs},
        })

        async with websockets.connect(self._ws_url, ping_interval=30) as ws:
            await ws.send(subscribe_msg)
            logger.info(f"[kraken][conn-{conn_id}] Subscribed to {len(pairs)} pairs")

            async for message in ws:
                data = json.loads(message)
                if data.get("channel") != "ticker":
                    continue
                if data.get("type") not in ("update", "snapshot"):
                    continue

                for item in data.get("data", []):
                    tick = RawTick(
                        exchange="kraken",
                        pair=item.get("symbol", ""),
                        data={
                            "bid":        item.get("bid", 0),
                            "ask":        item.get("ask", 0),
                            "last":       item.get("last", 0),
                            "vwap":       item.get("vwap", 0),
                            "volume_24h": item.get("volume", 0),
                            "high_24h":   item.get("high", 0),
                            "low_24h":    item.get("low", 0),
                        },
                        received_at=time.time(),
                    )
                    await self._emit(tick)
