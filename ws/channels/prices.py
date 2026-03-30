"""
Price channel — streams live price ticks to subscribed clients.

Multi-exchange support:
  - Aggregates prices from all exchanges (Kraken, Coinbase, etc.)
  - Calculates average price across all exchanges
  - Identifies best/worst priced exchanges for each coin

Redis pub/sub channel: rt:stream:prices
Routing key:           data["coin_id"]

Client subscribe message:
    { "action": "subscribe", "channel": "prices", "coins": ["bitcoin", "ethereum"] }

Outgoing message to client (enriched with multi-exchange data):
    {
        "channel": "prices",
        "data": {
            "coin_id": "bitcoin",
            "quote": "usd",
            "avg_price": 66025.50,
            "best_exchange": { "name": "kraken", "price": 66050.10 },
            "worst_exchange": { "name": "coinbase", "price": 66000.90 },
            "exchanges": {
                "kraken": {
                    "price": 66050.10,
                    "bid": 66050.0,
                    "ask": 66050.2,
                    "volume_24h": 3345.74,
                    "timestamp": 1774632034.49
                },
                "coinbase": {
                    "price": 66000.90,
                    "bid": 66000.8,
                    "ask": 66001.0,
                    "volume_24h": 2100.50,
                    "timestamp": 1774632035.12
                }
            },
            "exchange_count": 2,
            "timestamp": 1774632035.12
        }
    }
"""

import json
import logging
import time
from typing import Set

import websockets

from channels.base import Channel

logger = logging.getLogger(__name__)

# How long to keep exchange data before considering it stale (seconds)
EXCHANGE_DATA_TTL = 30.0


class ExchangePriceTracker:
    """
    Tracks prices from multiple exchanges for a single coin.
    
    Maintains a time-windowed cache of exchange prices and computes
    aggregates (average, best, worst) on demand.
    """
    
    def __init__(self, coin_id: str):
        self.coin_id = coin_id
        # exchange_name → { price, bid, ask, volume_24h, timestamp, ... }
        self._exchange_data: dict[str, dict] = {}
    
    def update(self, exchange: str, tick_data: dict) -> None:
        """Update price data from an exchange."""
        self._exchange_data[exchange] = {
            "price": tick_data.get("price") or tick_data.get("last"),
            "bid": tick_data.get("bid"),
            "ask": tick_data.get("ask"),
            "last": tick_data.get("last"),
            "vwap": tick_data.get("vwap"),
            "volume_24h": tick_data.get("volume_24h"),
            "spread_pct": tick_data.get("spread_pct"),
            "timestamp": tick_data.get("timestamp", time.time()),
        }
    
    def _prune_stale(self) -> None:
        """Remove exchange data older than TTL."""
        now = time.time()
        stale = [
            ex for ex, data in self._exchange_data.items()
            if now - data.get("timestamp", 0) > EXCHANGE_DATA_TTL
        ]
        for ex in stale:
            del self._exchange_data[ex]
    
    def get_aggregated(self) -> dict | None:
        """
        Return aggregated price data across all active exchanges.
        
        Returns None if no valid exchange data is available.
        """
        self._prune_stale()
        
        if not self._exchange_data:
            return None
        
        # Collect valid prices
        prices_by_exchange = {}
        for exchange, data in self._exchange_data.items():
            price = data.get("price")
            if price is not None and price > 0:
                prices_by_exchange[exchange] = price
        
        if not prices_by_exchange:
            return None
        
        # Calculate aggregates
        prices = list(prices_by_exchange.values())
        avg_price = sum(prices) / len(prices)
        
        # Find best (highest) and worst (lowest) exchanges
        best_exchange = max(prices_by_exchange, key=prices_by_exchange.get)
        worst_exchange = min(prices_by_exchange, key=prices_by_exchange.get)
        
        # Get most recent timestamp
        latest_timestamp = max(
            data.get("timestamp", 0) 
            for data in self._exchange_data.values()
        )
        
        return {
            "coin_id": self.coin_id,
            "quote": "usd",
            "avg_price": round(avg_price, 8),
            "best_exchange": {
                "name": best_exchange,
                "price": prices_by_exchange[best_exchange],
            },
            "worst_exchange": {
                "name": worst_exchange,
                "price": prices_by_exchange[worst_exchange],
            },
            "exchanges": {
                ex: {
                    "price": data.get("price"),
                    "bid": data.get("bid"),
                    "ask": data.get("ask"),
                    "volume_24h": data.get("volume_24h"),
                    "vwap": data.get("vwap"),
                    "spread_pct": data.get("spread_pct"),
                    "timestamp": data.get("timestamp"),
                }
                for ex, data in self._exchange_data.items()
            },
            "exchange_count": len(self._exchange_data),
            "timestamp": latest_timestamp,
        }


class PriceChannel(Channel):
    """
    Live price data from all exchanges with multi-exchange aggregation.
    
    When a price tick arrives from any exchange, this channel:
      1. Updates the per-exchange tracker for that coin
      2. Computes the average price across all active exchanges
      3. Identifies the best/worst priced exchanges
      4. Broadcasts the enriched data to subscribed clients
    """

    def __init__(self):
        super().__init__()
        # coin_id → ExchangePriceTracker
        self._trackers: dict[str, ExchangePriceTracker] = {}

    @property
    def name(self) -> str:
        return "prices"

    @property
    def redis_channel(self) -> str:
        return "rt:stream:prices"

    def _extract_routing_key(self, data: dict) -> str | None:
        return data.get("coin_id")
    
    def _get_or_create_tracker(self, coin_id: str) -> ExchangePriceTracker:
        """Get or create a price tracker for a coin."""
        if coin_id not in self._trackers:
            self._trackers[coin_id] = ExchangePriceTracker(coin_id)
        return self._trackers[coin_id]

    async def route(self, message: str) -> None:
        """
        Route a Redis pub/sub message to the correct subscribers.
        
        Overrides base class to add multi-exchange aggregation.
        """
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            logger.warning(f"[{self.name}] Invalid JSON from Redis: {message[:100]}")
            return

        coin_id = self._extract_routing_key(data)
        if not coin_id:
            return

        exchange = data.get("exchange", "unknown")
        
        # Update the tracker with this exchange's data
        tracker = self._get_or_create_tracker(coin_id)
        tracker.update(exchange, data)
        
        # Get aggregated data across all exchanges
        aggregated = tracker.get_aggregated()
        if not aggregated:
            return

        # Check if anyone is subscribed to this coin
        subscribers = self._subscriptions.get(coin_id, set())
        if not subscribers:
            return

        # Wrap with channel name
        outgoing = json.dumps({"channel": self.name, "data": aggregated})

        # Fan out to all subscribers
        disconnected: Set[websockets.WebSocketServerProtocol] = set()
        for ws in subscribers:
            try:
                await ws.send(outgoing)
            except websockets.ConnectionClosed:
                disconnected.add(ws)

        # Clean up dead connections
        for ws in disconnected:
            self.remove_client(ws)

    @property
    def stats(self) -> dict:
        """Extended stats including exchange tracking info."""
        base_stats = super().stats
        active_trackers = len(self._trackers)
        total_exchange_entries = sum(
            len(t._exchange_data) for t in self._trackers.values()
        )
        base_stats.update({
            "active_coin_trackers": active_trackers,
            "total_exchange_entries": total_exchange_entries,
        })
        return base_stats
