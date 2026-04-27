"""
Pionex trade connector.

Subscribes to the TRADE topic for individual trade executions.

Trade result fields:
  price — execution price
  size  — quantity
  side  — "BUY" or "SELL"
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


class PionexTradeConnector(BaseExchange):
    NAME = "pionex"

    def __init__(self, producer: StreamProducer):
        super().__init__(producer)
        self._ws_url = config.PIONEX_WS_URL

    def _load_pairs(self) -> List[str]:
        try:
            with open(config.ALIAS_JSON_PATH) as fp:
                alias_data = json.load(fp)
            pairs = []
            for entry in alias_data.get("assets", {}).values():
                sym = entry.get("exchange_symbols", {}).get("pionex")
                if sym:
                    pairs.append(f"{sym}_USDT")
            pairs = sorted(set(pairs))
            logger.info(f"[pionex-trades] Loaded {len(pairs)} USDT pairs")
            return pairs
        except Exception as e:
            logger.warning(f"[pionex-trades] Failed to load pairs: {e}")
            return ["BTC_USDT", "ETH_USDT", "SOL_USDT"]

    async def _connect_and_stream(self) -> None:
        pairs = self._load_pairs()
        if not pairs:
            await asyncio.sleep(30)
            return

        logger.info(f"[pionex-trades] Subscribing to {len(pairs)} pairs")

        async with websockets.connect(self._ws_url, ping_interval=None) as ws:
            for pair in pairs:
                await ws.send(json.dumps({
                    "op": "SUBSCRIBE",
                    "topic": "TRADE",
                    "symbol": pair,
                }))
                await asyncio.sleep(0.1)  # small delay to avoid throttling

            logger.info("[pionex-trades] Connected and subscribed")

            async for message in ws:
                data = json.loads(message)

                op = data.get("op", "")

                # Rate-limit close — raise so base class backs off
                if op == "CLOSE":
                    note = data.get("note", "")
                    raise RuntimeError(f"[pionex-trades] Server closed connection: {note}")

                # Respond to server pings
                if op == "PING":
                    await ws.send(json.dumps({"op": "PONG", "timestamp": int(time.time() * 1000)}))
                    continue

                if data.get("topic") != "TRADE":
                    continue

                symbol = data.get("symbol", "")
                for trade in data.get("data", []):
                    try:
                        price = float(trade["price"])
                        size = float(trade["size"])
                        side = trade.get("side", "BUY").lower()
                    except (KeyError, ValueError, TypeError):
                        continue

                    tick = RawTick(
                        exchange="pionex",
                        pair=symbol,
                        data={
                            "price": price,
                            "size": size,
                            "side": side,
                            "type": "trade",
                        },
                        received_at=time.time(),
                    )
                    await self._emit(tick)
