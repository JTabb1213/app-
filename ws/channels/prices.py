"""
Price channel — streams live price ticks to subscribed clients.

Redis pub/sub channel: rt:stream:prices
Routing key:           data["coin_id"]

Client subscribe message:
    { "action": "subscribe", "channel": "prices", "coins": ["bitcoin", "ethereum"] }

Outgoing message to client:
    {
        "channel": "prices",
        "data": {
            "coin_id": "bitcoin",
            "quote": "usd",
            "exchange": "kraken",
            "price": 66000.05,
            "bid": 66000.0,
            "ask": 66000.1,
            "last": 66000.1,
            "vwap": 67442.3,
            "volume_24h": 3345.74,
            "spread_pct": 0.0002,
            "timestamp": 1774632034.49
        }
    }
"""

from channels.base import Channel


class PriceChannel(Channel):
    """Live price data from all exchanges."""

    @property
    def name(self) -> str:
        return "prices"

    @property
    def redis_channel(self) -> str:
        return "rt:stream:prices"

    def _extract_routing_key(self, data: dict) -> str | None:
        return data.get("coin_id")
