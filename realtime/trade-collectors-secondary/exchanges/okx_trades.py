"""
OKX trade connector.

Subscribes to the "trades" channel for individual trade executions.

Trade fields:
  px   — price
  sz   — size
  side — "buy" or "sell"
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


class OkxTradeConnector(BaseExchange):
    NAME = "okx"

    def __init__(self, producer: StreamProducer):
        super().__init__(producer)
        self._ws_url = config.OKX_WS_URL

    def _load_pairs(self) -> List[str]:
        try:
            with open(config.ALIAS_JSON_PATH) as fp:
                alias_data = json.load(fp)
            pairs = []
            for entry in alias_data.get("assets", {}).values():
                sym = entry.get("exchange_symbols", {}).get("okx")
                if sym:
                    pairs.append(f"{sym}-USDT")  # e.g. ETH-USDT
            pairs = sorted(set(pairs))
            logger.info(f"[okx-trades] Loaded {len(pairs)} USDT pairs")
            return pairs
        except Exception as e:
            logger.warning(f"[okx-trades] Failed to load pairs: {e}")
            return ["BTC-USDT", "ETH-USDT", "SOL-USDT"]

    async def _connect_and_stream(self) -> None:
        pairs = self._load_pairs()
        if not pairs:
            await asyncio.sleep(30)
            return

        logger.info(f"[okx-trades] Subscribing to {len(pairs)} pairs")

        async with websockets.connect(self._ws_url, ping_interval=20) as ws:
            await ws.send(json.dumps({
                "op": "subscribe",
                "args": [{"channel": "trades", "instId": p} for p in pairs],
            }))
            logger.info("[okx-trades] Connected and subscribed")

            async for message in ws:
                data = json.loads(message)
                if "data" not in data or data.get("arg", {}).get("channel") != "trades":
                    continue

                for item in data["data"]:
                    try:
                        price = float(item["px"])
                        size = float(item["sz"])
                        side = item.get("side", "unknown")
                    except (KeyError, ValueError, TypeError):
                        continue

                    tick = RawTick(
                        exchange="okx",
                        pair=data["arg"]["instId"],
                        data={
                            "price": price,
                            "size": size,
                            "side": side,
                            "type": "trade",
                        },
                        received_at=time.time(),
                    )
                    await self._emit(tick)
