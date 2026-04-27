"""
Kraken trade connector.

Subscribes to the "trade" channel on Kraken WS v2 for individual
trade executions.

Trade data fields:
  price   — execution price
  qty     — quantity
  side    — "buy" or "sell"
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

V1_TO_V2 = {"XBT": "BTC", "XDG": "DOGE"}


class KrakenTradeConnector(BaseExchange):
    NAME = "kraken"

    def __init__(self, producer: StreamProducer):
        super().__init__(producer)
        self._ws_url = config.KRAKEN_WS_URL

    def _load_pairs(self) -> List[str]:
        try:
            with open(config.ALIAS_JSON_PATH) as fp:
                alias_data = json.load(fp)
            pairs = []
            for entry in alias_data.get("assets", {}).values():
                sym = entry.get("exchange_symbols", {}).get("kraken")
                if sym:
                    base = V1_TO_V2.get(sym, sym)
                    pairs.append(f"{base}/USD")    # e.g. ETH/USD
                    pairs.append(f"{base}/USDT")  # e.g. ETH/USDT
            pairs = sorted(set(pairs))
            logger.info(f"[kraken-trades] Loaded {len(pairs)} pairs (USD + USDT only)")
            return pairs
        except Exception as e:
            logger.warning(f"[kraken-trades] Failed to load pairs: {e}")
            return ["BTC/USD", "BTC/USDT", "ETH/USD", "ETH/USDT", "SOL/USD", "SOL/USDT"]

    async def _connect_and_stream(self) -> None:
        pairs = self._load_pairs()
        if not pairs:
            logger.warning("[kraken-trades] No pairs — sleeping 30s")
            await asyncio.sleep(30)
            return

        logger.info(f"[kraken-trades] Subscribing to {len(pairs)} pairs")

        async with websockets.connect(self._ws_url, ping_interval=30) as ws:
            await ws.send(json.dumps({
                "method": "subscribe",
                "params": {"channel": "trade", "symbol": pairs},
            }))
            logger.info("[kraken-trades] Connected and subscribed")

            async for message in ws:
                data = json.loads(message)
                if data.get("channel") != "trade":
                    continue
                if data.get("type") not in ("update", "snapshot"):
                    continue

                for item in data.get("data", []):
                    try:
                        price = float(item["price"])
                        qty = float(item["qty"])
                        side = item.get("side", "unknown")
                    except (KeyError, ValueError, TypeError):
                        continue

                    tick = RawTick(
                        exchange="kraken",
                        pair=item.get("symbol", ""),
                        data={
                            "price": price,
                            "size": qty,
                            "side": side,
                            "type": "trade",
                        },
                        received_at=time.time(),
                    )
                    await self._emit(tick)
