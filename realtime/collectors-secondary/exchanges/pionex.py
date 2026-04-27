"""
Pionex websocket connector.

Connects to Pionex's public WebSocket API, subscribes to the TRADE topic,
and emits RawTick events to the stream.

Docs: https://pionex-doc.gitbook.io/apidocs/websocket/public-stream/trade

Pionex specifics:
  - Pair format: "BTC_USDT" (underscore separated)
  - No TICKER topic available — only TRADE and DEPTH
  - TRADE gives individual trades: price, size, side, timestamp
  - No bid/ask from this stream (set to 0; ingestor will use last price)
  - Server sends PING, client must reply with PONG
  - Uses .us endpoint for US users by default

Note: TRADE fires on every individual trade (higher frequency than
ticker-based exchanges). The stream producer's batching handles this.
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


class PionexConnector(BaseExchange):
    NAME = "pionex"

    def __init__(
        self,
        producer: StreamProducer,
        quote_currencies: Optional[List[str]] = None,
    ):
        super().__init__(producer)
        self._ws_url = config.PIONEX_WS_URL
        self._rest_url = config.PIONEX_REST_URL
        self._quote_currencies = quote_currencies or config.QUOTE_CURRENCIES
        self._pairs: List[str] = []

    # -- Symbol discovery ---------------------------------------------------

    def _load_pairs_from_json(self) -> List[str]:
        """Build Pionex pairs from coin_aliases.json standard symbols."""
        try:
            with open(config.ALIAS_JSON_PATH) as fp:
                alias_data = json.load(fp)
            pairs = []
            for entry in alias_data.get("assets", {}).values():
                symbol = entry.get("symbol", "")
                if symbol:
                    for quote in self._quote_currencies:
                        pairs.append(f"{symbol}_{quote}")
            pairs = sorted(set(pairs))
            if pairs:
                logger.info(f"[pionex] Built {len(pairs)} pairs from coin_aliases.json")
                return pairs
        except Exception as e:
            logger.warning(f"[pionex] Failed to load pairs from JSON: {e}")
        return []

    async def _fetch_pairs_from_api(self) -> List[str]:
        """Fetch available symbols from Pionex REST API."""
        try:
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=10)
                async with session.get(self._rest_url, timeout=timeout) as resp:
                    data = await resp.json()
            pairs = []
            result = data.get("data", {}).get("symbols", [])
            for item in result:
                symbol = item.get("symbol", "")          # e.g. "BTC_USDT"
                quote = item.get("quoteCurrency", "")
                enable = item.get("enable", False)
                if quote.upper() in self._quote_currencies and enable:
                    pairs.append(symbol)
            pairs = sorted(set(pairs))
            logger.info(f"[pionex] Fetched {len(pairs)} pairs from API (fallback)")
            return pairs
        except Exception as e:
            logger.error(f"[pionex] API fallback failed: {e}")
            return []

    async def _fetch_pairs(self) -> List[str]:
        pairs = self._load_pairs_from_json()
        if pairs:
            return pairs
        pairs = await self._fetch_pairs_from_api()
        if pairs:
            return pairs
        logger.warning("[pionex] Using hardcoded seed pairs (last resort)")
        return ["BTC_USDT", "ETH_USDT", "SOL_USDT", "XRP_USDT", "ADA_USDT",
                "DOGE_USDT", "AVAX_USDT", "DOT_USDT", "LINK_USDT", "LTC_USDT"]

    # -- WebSocket streaming ------------------------------------------------

    async def _connect_and_stream(self) -> None:
        self._pairs = await self._fetch_pairs()

        if not self._pairs:
            logger.warning("[pionex] No pairs — sleeping 30s")
            await asyncio.sleep(30)
            return

        logger.info(f"[pionex] Subscribing to {len(self._pairs)} TRADE streams")

        # Disable library ping — Pionex uses custom PING/PONG protocol
        async with websockets.connect(self._ws_url, ping_interval=None) as ws:
            # Subscribe in batches of 10 with a pause between batches.
            # Sending all 51 subs rapidly causes the server to send CLOSE.
            BATCH = 10
            for i in range(0, len(self._pairs), BATCH):
                batch = self._pairs[i:i + BATCH]
                for pair in batch:
                    await ws.send(json.dumps({
                        "op": "SUBSCRIBE",
                        "topic": "TRADE",
                        "symbol": pair,
                    }))
                await asyncio.sleep(0.5)  # 500ms between batches

            logger.info(f"[pionex] Sent {len(self._pairs)} TRADE subscriptions")

            async for message in ws:
                data = json.loads(message)
                op = data.get("op", "")

                # Server PING → reply with PONG
                if op == "PING":
                    pong = json.dumps({
                        "op": "PONG",
                        "timestamp": int(time.time() * 1000),
                    })
                    await ws.send(pong)
                    continue

                if op == "CLOSE":
                    logger.warning("[pionex] Server sent CLOSE")
                    break

                # Subscription ack
                if data.get("type") in ("SUBSCRIBED", "UNSUBSCRIBED"):
                    continue

                topic = data.get("topic", "")
                symbol = data.get("symbol", "")

                if topic != "TRADE" or not symbol:
                    continue

                trades = data.get("data", [])
                for trade in trades:
                    try:
                        price = float(trade.get("price", 0) or 0)
                    except (ValueError, TypeError):
                        continue

                    if price <= 0:
                        continue

                    # TRADE only gives price/size/side — no bid/ask
                    tick = RawTick(
                        exchange="pionex",
                        pair=symbol,
                        data={
                            "bid": 0, "ask": 0, "last": price,
                            "vwap": None, "volume_24h": None,
                        },
                        received_at=time.time(),
                    )
                    await self._emit(tick)
