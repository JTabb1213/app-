"""
Kraken websocket connector.

Connects to Kraken's WebSocket v2 API, subscribes to the ticker channel
for all tradeable USD pairs, and emits RawTick events onto the ingestion
queue.

Ticker channel docs:
  https://docs.kraken.com/api/docs/websocket-v2/ticker

Why ticker over trade:
  - ticker fires on every best-bid/ask change (order book quote updates)
  - trade only fires on executed deals (can be seconds apart in thin markets)
  - ticker gives us bid, ask, last, vwap — everything we need for live price

Message format (v2 ticker):
  {
    "channel": "ticker",
    "type": "update",
    "data": [{
      "symbol": "BTC/USD",
      "bid": 65432.1, "bid_qty": 1.5,
      "ask": 65433.0, "ask_qty": 2.0,
      "last": 65432.5, "volume": 1234.5,
      "vwap": 65400.0, ...
    }]
  }
"""

import asyncio
import json
import logging
import time
from typing import List, Optional

import aiohttp
import websockets

import config
from core.models import RawTick
from exchanges.base import BaseExchange

logger = logging.getLogger(__name__)


class KrakenConnector(BaseExchange):
    """
    Kraken exchange websocket connector.

    Lifecycle:
      1. Fetch all tradeable pairs from Kraken REST API
      2. Filter to configured quote currencies (default: USD only)
      3. Chunk pairs into batches of ~200 (Kraken's per-connection limit)
      4. Open one websocket per chunk, subscribe to ticker channel
      5. Parse incoming ticker messages → RawTick → ingestion queue
    """

    NAME = "kraken"

    def __init__(
        self,
        queue: asyncio.Queue,
        quote_currencies: Optional[List[str]] = None,
    ):
        super().__init__(queue)
        self._ws_url = config.KRAKEN_WS_URL
        self._rest_url = config.KRAKEN_REST_URL
        self._chunk_size = config.KRAKEN_CHUNK_SIZE
        self._quote_currencies = quote_currencies or config.QUOTE_CURRENCIES
        self._pairs: List[str] = []

    # ------------------------------------------------------------------
    # Pair discovery via REST API
    # ------------------------------------------------------------------

    async def _fetch_pairs(self) -> List[str]:
        """
        Fetch all tradeable pairs from Kraken's REST API.
        Filters to pairs quoted in our configured currencies.

        Returns a list of wsname strings like ["XBT/USD", "ETH/USD", ...].
        """
        try:
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=10)
                async with session.get(self._rest_url, timeout=timeout) as resp:
                    data = await resp.json()

            pairs = []
            for key, val in data.get("result", {}).items():
                wsname = val.get("wsname")
                if not wsname or ".d" in key:
                    continue    # skip dark-pool entries

                # Filter by quote currency: "XBT/USD" → quote is "USD"
                quote = wsname.split("/")[-1] if "/" in wsname else None
                if quote and quote.upper() in self._quote_currencies:
                    pairs.append(wsname)

            pairs = sorted(set(pairs))
            logger.info(
                f"[kraken] Fetched {len(pairs)} pairs "
                f"(quote filter: {self._quote_currencies})"
            )
            return pairs

        except Exception as e:
            logger.error(f"[kraken] Failed to fetch pairs: {e} — using fallback")
            return ["XBT/USD", "ETH/USD", "SOL/USD", "XRP/USD", "ADA/USD"]

    # ------------------------------------------------------------------
    # WebSocket streaming
    # ------------------------------------------------------------------

    async def _connect_and_stream(self) -> None:
        """
        Connect to Kraken WS v2, subscribe to ticker for all pairs,
        and emit RawTick events to the ingestion queue.

        If we have more pairs than CHUNK_SIZE, spawns multiple websocket
        connections in parallel (one per chunk).
        """
        self._pairs = await self._fetch_pairs()

        if not self._pairs:
            logger.warning("[kraken] No pairs to subscribe to — sleeping 30s")
            await asyncio.sleep(30)
            return

        # Chunk pairs to respect Kraken's per-connection subscription limit
        chunks = [
            self._pairs[i : i + self._chunk_size]
            for i in range(0, len(self._pairs), self._chunk_size)
        ]

        logger.info(
            f"[kraken] Spawning {len(chunks)} connection(s) "
            f"for {len(self._pairs)} pairs"
        )

        # Run all chunk listeners concurrently — if one fails the gather
        # propagates the exception, and the base class handles reconnection
        await asyncio.gather(
            *[self._stream_chunk(i, chunk) for i, chunk in enumerate(chunks)]
        )

    async def _stream_chunk(self, conn_id: int, pairs: List[str]) -> None:
        """
        Single websocket connection handling one chunk of pairs.

        Subscribes to the v2 ticker channel and loops forever,
        parsing messages and emitting RawTick events.
        """
        # ── Kraken v2 subscribe message ──
        subscribe_msg = json.dumps({
            "method": "subscribe",
            "params": {
                "channel": "ticker",
                "symbol": pairs,
            },
        })

        async with websockets.connect(self._ws_url, ping_interval=30) as ws:
            await ws.send(subscribe_msg)
            logger.info(
                f"[kraken][conn-{conn_id}] Subscribed to ticker "
                f"for {len(pairs)} pairs"
            )

            async for message in ws:
                data = json.loads(message)

                # ── v2 format: data messages have "channel" key ──
                channel = data.get("channel")
                if channel != "ticker":
                    continue    # skip heartbeats, subscription confirmations, etc.

                msg_type = data.get("type")
                if msg_type not in ("update", "snapshot"):
                    continue

                for item in data.get("data", []):
                    pair = item.get("symbol", "")

                    tick = RawTick(
                        exchange="kraken",
                        pair=pair,
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
