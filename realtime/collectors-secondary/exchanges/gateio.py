"""
Gate.io websocket connector.

Connects to Gate.io's WebSocket v4 API, subscribes to the spot.tickers
channel, and emits RawTick events to the stream.

Docs: https://www.gate.io/docs/developers/apiv4/ws/en/

Gate.io specifics:
  - Pair format: "BTC_USDT" (underscore separated)
  - Requires manual PING every ~10s (spot.ping channel)
  - Ticker gives: highest_bid, lowest_ask, last, base_volume
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


class GateioConnector(BaseExchange):
    NAME = "gateio"

    def __init__(
        self,
        producer: StreamProducer,
        quote_currencies: Optional[List[str]] = None,
    ):
        super().__init__(producer)
        self._ws_url = config.GATEIO_WS_URL
        self._rest_url = config.GATEIO_REST_URL
        self._ping_interval = config.GATEIO_PING_INTERVAL
        self._quote_currencies = quote_currencies or config.QUOTE_CURRENCIES
        self._pairs: List[str] = []

    # -- Symbol discovery ---------------------------------------------------

    def _load_pairs_from_json(self) -> List[str]:
        """Build Gate.io pairs from coin_aliases.json standard symbols."""
        try:
            with open(config.ALIAS_JSON_PATH) as fp:
                alias_data = json.load(fp)
            pairs = []
            for entry in alias_data.get("assets", {}).values():
                symbol = entry.get("symbol", "")
                if symbol:
                    for quote in self._quote_currencies:
                        # Skip invalid self-referencing pairs like USDT_USDT, USDC_USDT
                        if symbol.upper() == quote.upper():
                            continue
                        pairs.append(f"{symbol}_{quote}")
            pairs = sorted(set(pairs))
            if pairs:
                logger.info(f"[gateio] Built {len(pairs)} pairs from coin_aliases.json")
                return pairs
        except Exception as e:
            logger.warning(f"[gateio] Failed to load pairs from JSON: {e}")
        return []

    async def _fetch_pairs_from_api(self) -> List[str]:
        """Fetch available pairs from Gate.io REST API."""
        try:
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=10)
                async with session.get(self._rest_url, timeout=timeout) as resp:
                    data = await resp.json()
            pairs = []
            for item in data:
                pair_id = item.get("id", "")     # e.g. "BTC_USDT"
                quote = item.get("quote", "")     # e.g. "USDT"
                status = item.get("trade_status", "")
                if quote.upper() in self._quote_currencies and status == "tradable":
                    pairs.append(pair_id)
            pairs = sorted(set(pairs))
            logger.info(f"[gateio] Fetched {len(pairs)} pairs from API (fallback)")
            return pairs
        except Exception as e:
            logger.error(f"[gateio] API fallback failed: {e}")
            return []

    async def _fetch_pairs(self) -> List[str]:
        pairs = self._load_pairs_from_json()
        if pairs:
            return pairs
        pairs = await self._fetch_pairs_from_api()
        if pairs:
            return pairs
        logger.warning("[gateio] Using hardcoded seed pairs (last resort)")
        return ["BTC_USDT", "ETH_USDT", "SOL_USDT", "XRP_USDT", "ADA_USDT",
                "DOGE_USDT", "AVAX_USDT", "DOT_USDT", "LINK_USDT", "LTC_USDT"]

    # -- WebSocket streaming ------------------------------------------------

    async def _connect_and_stream(self) -> None:
        self._pairs = await self._fetch_pairs()

        if not self._pairs:
            logger.warning("[gateio] No pairs — sleeping 30s")
            await asyncio.sleep(30)
            return

        logger.info(f"[gateio] Subscribing to {len(self._pairs)} pairs")

        async with websockets.connect(self._ws_url, ping_interval=None) as ws:
            # Subscribe one pair at a time — Gate.io rejects the entire batch
            # if any single pair is invalid (e.g. EOS_USDT not listed)
            for pair in self._pairs:
                await ws.send(json.dumps({
                    "time": int(time.time()),
                    "channel": "spot.tickers",
                    "event": "subscribe",
                    "payload": [pair],
                }))
                await asyncio.sleep(0.02)  # 20ms between subs

            logger.info("[gateio] Sent individual subscribe messages for all pairs")

            last_ping = time.time()
            tick_count = 0

            async for message in ws:
                tick_count += 1
                # Manual ping every N seconds (Gate.io doesn't use standard WS ping)
                if time.time() - last_ping >= self._ping_interval:
                    await ws.send(json.dumps({
                        "time": int(time.time()),
                        "channel": "spot.ping",
                    }))
                    last_ping = time.time()

                data = json.loads(message)
                channel = data.get("channel", "")
                event = data.get("event", "")

                # Skip pong messages
                if channel == "spot.pong":
                    continue

                # Log subscribe acks — surface any errors from Gate.io
                if event == "subscribe":
                    error = data.get("error")
                    if error:
                        logger.warning(f"[gateio] Subscribe error: {error}")
                    continue

                if event == "unsubscribe":
                    continue

                if channel != "spot.tickers" or event != "update":
                    logger.debug(f"[gateio] Unhandled message: channel={channel!r} event={event!r}")
                    continue

                result = data.get("result", {})
                pair = result.get("currency_pair", "")
                if not pair:
                    continue

                try:
                    bid = float(result.get("highest_bid", 0) or 0)
                    ask = float(result.get("lowest_ask", 0) or 0)
                    last = float(result.get("last", 0) or 0)
                    volume = float(result.get("base_volume", 0) or 0)
                except (ValueError, TypeError):
                    continue

                tick = RawTick(
                    exchange="gateio",
                    pair=pair,
                    data={
                        "bid": bid, "ask": ask, "last": last,
                        "vwap": None, "volume_24h": volume,
                    },
                    received_at=time.time(),
                )
                await self._emit(tick)
        logger.warning(f"[gateio] WebSocket closed after {tick_count} messages — will reconnect")