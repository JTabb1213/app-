"""
MEXC trade connector.

Subscribes to "spot@public.deals.v3.api@{SYMBOL}" channels.

Result fields:
  p — price
  v — volume (quantity)
  S — side: 1 = buy, 2 = sell
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


class MexcTradeConnector(BaseExchange):
    NAME = "mexc"

    def __init__(self, producer: StreamProducer):
        super().__init__(producer)
        self._ws_url = config.MEXC_WS_URL

    def _load_pairs(self) -> List[str]:
        try:
            with open(config.ALIAS_JSON_PATH) as fp:
                alias_data = json.load(fp)
            pairs = []
            for entry in alias_data.get("assets", {}).values():
                sym = entry.get("exchange_symbols", {}).get("mexc")
                if sym:
                    pairs.append(f"{sym}USDT")  # e.g. ETHUSDT
            pairs = sorted(set(pairs))
            logger.info(f"[mexc-trades] Loaded {len(pairs)} USDT pairs\")")
            return pairs
        except Exception as e:
            logger.warning(f"[mexc-trades] Failed to load pairs: {e}")
            return ["BTCUSDT", "ETHUSDT", "ETHBTC", "SOLUSDT", "SOLBTC"]

    async def _connect_and_stream(self) -> None:
        pairs = self._load_pairs()
        if not pairs:
            await asyncio.sleep(30)
            return

        logger.info(f"[mexc-trades] Subscribing to {len(pairs)} pairs")

        async with websockets.connect(self._ws_url, ping_interval=20) as ws:
            # MEXC supports batch subscription via params list
            params = [f"spot@public.deals.v3.api@{p}" for p in pairs]
            await ws.send(json.dumps({
                "method": "SUBSCRIPTION",
                "params": params,
            }))
            logger.info("[mexc-trades] Connected and subscribed")

            async for message in ws:
                data = json.loads(message)

                # MEXC sends ping frames we must pong
                if "ping" in data:
                    await ws.send(json.dumps({"pong": data["ping"]}))
                    continue

                channel = data.get("c", "")
                if "public.deals" not in channel:
                    continue

                deals = data.get("d", {}).get("deals", [])
                for deal in deals:
                    try:
                        price = float(deal["p"])
                        size = float(deal["v"])
                        side_code = deal.get("S", 1)
                        side = "buy" if side_code == 1 else "sell"
                    except (KeyError, ValueError, TypeError):
                        continue

                    pair = channel.split("@")[-1] if "@" in channel else channel

                    tick = RawTick(
                        exchange="mexc",
                        pair=pair,
                        data={
                            "price": price,
                            "size": size,
                            "side": side,
                            "type": "trade",
                        },
                        received_at=time.time(),
                    )
                    await self._emit(tick)
