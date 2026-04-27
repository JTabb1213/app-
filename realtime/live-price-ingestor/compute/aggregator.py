"""
Price Aggregator — computes avg, best, worst across exchanges.

Maintains a rolling window of exchange prices per coin and
computes aggregates on demand.
"""

import time
from dataclasses import dataclass
from typing import Dict, Optional, Set

from shared.models import NormalizedTick

EXCHANGE_STALENESS_TTL = 120.0  # 2 min — accommodates slower exchanges like Gate.io


@dataclass
class ExchangeSnapshot:
    """Snapshot of a single exchange's price for a coin."""
    exchange: str
    price: float
    bid: float
    ask: float
    last: float
    vwap: Optional[float]
    volume_24h: Optional[float]
    spread_pct: float
    timestamp: float

    @classmethod
    def from_tick(cls, tick: NormalizedTick) -> "ExchangeSnapshot":
        return cls(
            exchange=tick.exchange,
            price=tick.price,
            bid=tick.bid,
            ask=tick.ask,
            last=tick.last,
            vwap=tick.vwap,
            volume_24h=tick.volume_24h,
            spread_pct=tick.spread_pct,
            timestamp=tick.timestamp,
        )

    def to_dict(self) -> dict:
        return {
            "exchange": self.exchange,
            "price": self.price,
            "bid": self.bid,
            "ask": self.ask,
            "last": self.last,
            "vwap": self.vwap,
            "volume_24h": self.volume_24h,
            "spread_pct": self.spread_pct,
            "timestamp": self.timestamp,
        }


class PriceAggregator:
    """
    Tracks prices from multiple exchanges per coin and computes aggregates.
    Maintains an in-memory cache of the latest price from each exchange
    for each coin. Prunes stale data automatically.
    """

    def __init__(self, staleness_ttl: float = EXCHANGE_STALENESS_TTL):
        self._data: Dict[str, Dict[str, ExchangeSnapshot]] = {}
        self._staleness_ttl = staleness_ttl

    def update(self, tick: NormalizedTick) -> None:
        coin_id = tick.coin_id
        if coin_id not in self._data:
            self._data[coin_id] = {}
        self._data[coin_id][tick.exchange] = ExchangeSnapshot.from_tick(tick)

    def update_batch(self, ticks: list) -> Set[str]:
        updated_coins = set()
        for tick in ticks:
            self.update(tick)
            updated_coins.add(tick.coin_id)
        return updated_coins

    def _prune_stale(self, coin_id: str) -> None:
        if coin_id not in self._data:
            return
        now = time.time()
        stale = [
            ex for ex, snap in self._data[coin_id].items()
            if now - snap.timestamp > self._staleness_ttl
        ]
        for ex in stale:
            del self._data[coin_id][ex]

    def get_aggregates(self, coin_id: str) -> Optional[dict]:
        self._prune_stale(coin_id)
        exchanges = self._data.get(coin_id, {})
        if not exchanges:
            return None

        valid = {
            ex: snap for ex, snap in exchanges.items()
            if snap.price > 0
        }
        if not valid:
            return None

        prices = [snap.price for snap in valid.values()]
        avg_price = sum(prices) / len(prices)

        highest_ex = max(valid, key=lambda ex: valid[ex].price)
        lowest_ex = min(valid, key=lambda ex: valid[ex].price)

        return {
            "coin_id": coin_id,
            "avg_price": round(avg_price, 8),
            "highest": valid[highest_ex],
            "lowest": valid[lowest_ex],
            "exchange_count": len(valid),
            "exchanges": valid,
            "timestamp": time.time(),
        }

    def get_all_coins(self) -> Set[str]:
        return set(self._data.keys())

    @property
    def stats(self) -> dict:
        total_exchanges = sum(len(exs) for exs in self._data.values())
        return {
            "coins_tracked": len(self._data),
            "total_exchange_entries": total_exchanges,
        }
