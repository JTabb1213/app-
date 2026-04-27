"""
Gate.io trade connector.

Subscribes to the "spot.trades" channel for individual trade executions.

Trade result fields:
  price  — execution price
  amount — quantity
  side   — "buy" or "sell"
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

PING_INTERVAL = 10


class GateioTradeConnector(BaseExchange):
    NAME = "gateio"

    def __init__(self, producer: StreamProducer):
        super().__init__(producer)
        self._ws_url = config.GATEIO_WS_URL

    def _load_pairs(self) -> List[str]:
        try:
            with open(config.ALIAS_JSON_PATH) as fp:
                alias_data = json.load(fp)
            pairs = []
            for entry in alias_data.get("assets", {}).values():
                sym = entry.get("exchange_symbols", {}).get("gateio")
                if sym:
                    pairs.append(f"{sym}_USDT")  # e.g. ETH_USDT
            pairs = sorted(set(pairs))
            logger.info(f"[gateio-trades] Loaded {len(pairs)} USDT pairs")
            return pairs
        except Exception as e:
            logger.warning(f"[gateio-trades] Failed to load pairs: {e}")
            return ["BTC_USDT", "ETH_USDT", "SOL_USDT"]

    async def _subscribe(self, ws, pairs: List[str]) -> None:
        await ws.send(json.dumps({
            "time": int(time.time()),
            "channel": "spot.trades",
            "event": "subscribe",
            "payload": pairs,
        }))

    async def _connect_and_stream(self) -> None:
        pairs = self._load_pairs()
        if not pairs:
            await asyncio.sleep(30)
            return

        logger.info(f"[gateio-trades] Subscribing to {len(pairs)} pairs")

        async with websockets.connect(self._ws_url, ping_interval=None) as ws:
            await self._subscribe(ws, pairs)
            logger.info("[gateio-trades] Connected and subscribed")

            last_ping = time.time()
            async for message in ws:
                now = time.time()
                if now - last_ping >= PING_INTERVAL:
                    await ws.send(json.dumps({
                        "time": int(time.time()),
                        "channel": "spot.ping",
                    }))
                    last_ping = now

                data = json.loads(message)

                # Handle unknown pair errors — remove and resubscribe
                if (data.get("event") == "subscribe" and
                        data.get("result", {}).get("status") == "fail"):
                    err_msg = data.get("error", {}).get("message", "")
                    bad = err_msg.replace("unknown currency pair: ", "").strip()
                    if bad and bad in pairs:
                        pairs.remove(bad)
                        logger.warning(f"[gateio-trades] Removed unknown pair '{bad}', resubscribing {len(pairs)} pairs")
                        await self._subscribe(ws, pairs)
                    continue

                if data.get("channel") != "spot.trades" or data.get("event") != "update":
                    continue

                result = data.get("result", {})
                try:
                    price = float(result["price"])
                    amount = float(result["amount"])
                    side = result.get("side", "unknown")
                    pair_name = result.get("currency_pair", "")
                except (KeyError, ValueError, TypeError):
                    continue

                tick = RawTick(
                    exchange="gateio",
                    pair=pair_name,
                    data={
                        "price": price,
                        "size": amount,
                        "side": side,
                        "type": "trade",
                    },
                    received_at=time.time(),
                )
                await self._emit(tick)
