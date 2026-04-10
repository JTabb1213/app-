"""
OKX websocket connector.

Connects to OKX's v5 WebSocket API, subscribes to the tickers channel,
and emits RawTick events to the stream.

Docs: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-ws-tickers-channel

OKX specifics:
  - Pair format: "BTC-USDT" (dash separated)
  - Tickers channel gives: last, bidPx, askPx, vol24h, open24h
  - Standard WS ping/pong (library handles it)
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


class OkxConnector(BaseExchange):
    NAME = "okx"

    def __init__(
        self,
        producer: StreamProducer,
        quote_currencies: Optional[List[str]] = None,
    ):
        super().__init__(producer)
        self._ws_url = config.OKX_WS_URL
        self._rest_url = config.OKX_REST_URL
        self._quote_currencies = quote_currencies or config.QUOTE_CURRENCIES
        self._pairs: List[str] = []

    # -- Symbol discovery ---------------------------------------------------

    def _load_pairs_from_json(self) -> List[str]:
        """Build OKX instIds from coin_aliases.json standard symbols."""
        try:
            with open(config.ALIAS_JSON_PATH) as fp:
                alias_data = json.load(fp)
            pairs = []
            for entry in alias_data.get("assets", {}).values():
                symbol = entry.get("symbol", "")
                if symbol:
                    for quote in self._quote_currencies:
                        pairs.append(f"{symbol}-{quote}")
            pairs = sorted(set(pairs))
            if pairs:
                logger.info(f"[okx] Built {len(pairs)} pairs from coin_aliases.json")
                return pairs
        except Exception as e:
            logger.warning(f"[okx] Failed to load pairs from JSON: {e}")
        return []

    async def _fetch_pairs_from_api(self) -> List[str]:
        """Fetch available instruments from OKX REST API."""
        try:
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=10)
                async with session.get(self._rest_url, timeout=timeout) as resp:
                    data = await resp.json()
            pairs = []
            for item in data.get("data", []):
                inst_id = item.get("instId", "")        # e.g. "BTC-USDT"
                state = item.get("state", "")
                quote = item.get("quoteCcy", "")
                if quote.upper() in self._quote_currencies and state == "live":
                    pairs.append(inst_id)
            pairs = sorted(set(pairs))
            logger.info(f"[okx] Fetched {len(pairs)} pairs from API (fallback)")
            return pairs
        except Exception as e:
            logger.error(f"[okx] API fallback failed: {e}")
            return []

    async def _fetch_pairs(self) -> List[str]:
        pairs = self._load_pairs_from_json()
        if pairs:
            return pairs
        pairs = await self._fetch_pairs_from_api()
        if pairs:
            return pairs
        logger.warning("[okx] Using hardcoded seed pairs (last resort)")
        return ["BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "ADA-USDT",
                "DOGE-USDT", "AVAX-USDT", "DOT-USDT", "LINK-USDT", "LTC-USDT"]

    # -- WebSocket streaming ------------------------------------------------

    async def _connect_and_stream(self) -> None:
        self._pairs = await self._fetch_pairs()

        if not self._pairs:
            logger.warning("[okx] No pairs — sleeping 30s")
            await asyncio.sleep(30)
            return

        logger.info(f"[okx] Subscribing to {len(self._pairs)} pairs")

        subscribe_msg = json.dumps({
            "op": "subscribe",
            "args": [
                {"channel": "tickers", "instId": pair}
                for pair in self._pairs
            ],
        })

        async with websockets.connect(self._ws_url, ping_interval=20) as ws:
            await ws.send(subscribe_msg)
            logger.info("[okx] Subscribed to tickers channel")

            async for message in ws:
                data = json.loads(message)

                # Handle subscription confirmations and errors
                if "event" in data:
                    event = data.get("event", "")
                    if event == "error":
                        logger.warning(f"[okx] Error: {data.get('msg', 'unknown')}")
                    continue

                arg = data.get("arg", {})
                if arg.get("channel") != "tickers":
                    continue

                for item in data.get("data", []):
                    pair = item.get("instId", "")
                    if not pair:
                        continue

                    try:
                        bid = float(item.get("bidPx", 0) or 0)
                        ask = float(item.get("askPx", 0) or 0)
                        last = float(item.get("last", 0) or 0)
                        volume = float(item.get("vol24h", 0) or 0)
                    except (ValueError, TypeError):
                        continue

                    tick = RawTick(
                        exchange="okx",
                        pair=pair,
                        data={
                            "bid": bid, "ask": ask, "last": last,
                            "vwap": None, "volume_24h": volume,
                        },
                        received_at=time.time(),
                    )
                    await self._emit(tick)
