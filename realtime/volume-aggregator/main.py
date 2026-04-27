#!/usr/bin/env python3
"""
Volume Aggregator Service
=========================

Consumes trade ticks from Redis Stream ``stream:trades:volume``,
resolves coin aliases, computes notional value, and accumulates
buy/sell volume into per-minute Redis hash buckets.

Redis key design:
    vol:{coin_id}  — HASH  (TTL = 25 h)
        field = minute_ts (str)  →  value = JSON {"b": float, "s": float}

The REST API (backend/routes/volume.py) reads these hashes on demand
to produce windowed volume totals.
"""

import asyncio
import json
import logging
import os
import sys
import time
from collections import defaultdict

_parent = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
if os.path.isdir(os.path.join(_parent, "shared")):
    sys.path.insert(0, _parent)

from aiohttp import web
import redis.asyncio as aioredis

import config
from shared.models import RawTick
from shared.stream.consumer import StreamConsumer

# ── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s │ %(levelname)-7s │ %(name)-20s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("volume-aggregator")
logging.getLogger("aiohttp").setLevel(logging.WARNING)

# ── Alias resolver ────────────────────────────────────────────────────────

_pair_to_coin: dict[str, str] = {}


def _build_alias_map():
    """Build a reverse lookup: (exchange, PAIR) → coin_id."""
    global _pair_to_coin
    try:
        with open(config.ALIAS_JSON_PATH) as fp:
            data = json.load(fp)
        for coin_id, entry in data.get("assets", {}).items():
            for exchange, sym in entry.get("exchange_symbols", {}).items():
                # Collectors emit pairs like "BTCUSDT", "BTC_USDT", "BTC/USD" etc.
                # We index several common suffixed forms.
                for suffix in ["USDT", "_USDT", "/USD", "USD", "/USDT", "-USD", "-USDT"]:
                    key = f"{exchange}:{sym}{suffix}".lower()
                    _pair_to_coin[key] = coin_id
                # Also store raw sym in case pair already matches
                _pair_to_coin[f"{exchange}:{sym}".lower()] = coin_id
        logger.info(f"Alias map built — {len(_pair_to_coin)} entries")
    except Exception as e:
        logger.error(f"Failed to build alias map: {e}")


def resolve_coin_id(exchange: str, pair: str) -> str | None:
    key = f"{exchange}:{pair}".lower()
    coin_id = _pair_to_coin.get(key)
    if coin_id:
        return coin_id
    # Try stripping common quote suffixes for a partial match
    for suffix in ["usdt", "_usdt", "/usd", "usd", "/usdt", "-usd", "-usdt"]:
        if key.endswith(suffix):
            base_key = key[: -len(suffix)]
            for s2 in ["usdt", "_usdt", "/usd", "usd", "/usdt", "-usd", "-usdt", ""]:
                cid = _pair_to_coin.get(base_key + s2)
                if cid:
                    return cid
    return None


# ── In-memory accumulator ────────────────────────────────────────────────
# {coin_id: {minute_ts: {"b": float, "s": float, "ex": set}}}
def _empty_bucket():
    return {"b": 0.0, "s": 0.0, "ex": set()}

_accum: dict[str, dict[int, dict]] = defaultdict(lambda: defaultdict(_empty_bucket))
_unresolved = 0
_processed = 0

# ── Stats ─────────────────────────────────────────────────────────────────
_consumer: StreamConsumer | None = None


async def _flush_to_redis(redis_client: aioredis.Redis):
    """Flush accumulated volume buckets to Redis hashes."""
    global _accum
    if not _accum:
        return

    snapshot = dict(_accum)
    _accum = defaultdict(lambda: defaultdict(_empty_bucket))

    pipe = redis_client.pipeline(transaction=False)
    ttl_seconds = config.VOLUME_KEY_TTL_HOURS * 3600

    for coin_id, buckets in snapshot.items():
        key = f"vol:{coin_id}"
        for minute_ts, volumes in buckets.items():
            # HINCRBY doesn't work on JSON, so we use a Lua-free approach:
            # Read existing, add, write back. For high throughput a Lua script
            # would be better, but this is fine for our scale.
            pipe.hget(key, str(minute_ts))

    # Execute reads
    existing = await pipe.execute()

    pipe2 = redis_client.pipeline(transaction=False)
    idx = 0
    for coin_id, buckets in snapshot.items():
        key = f"vol:{coin_id}"
        for minute_ts, volumes in buckets.items():
            old_raw = existing[idx]
            idx += 1
            if old_raw:
                try:
                    old = json.loads(old_raw)
                    volumes["b"] += old.get("b", 0.0)
                    volumes["s"] += old.get("s", 0.0)
                    # Merge previously stored exchanges with new ones
                    old_ex = set(old.get("ex", []))
                    volumes["ex"] = sorted(old_ex | volumes["ex"])
                except (json.JSONDecodeError, TypeError):
                    volumes["ex"] = sorted(volumes["ex"])
            else:
                volumes["ex"] = sorted(volumes["ex"])
            pipe2.hset(key, str(minute_ts), json.dumps(volumes))
        pipe2.expire(key, ttl_seconds)

    await pipe2.execute()
    logger.debug(f"Flushed {sum(len(b) for b in snapshot.values())} buckets for {len(snapshot)} coins")


async def _prune_old_buckets(redis_client: aioredis.Redis):
    """Remove minute buckets older than TTL from volume hashes."""
    cutoff = int(time.time()) - (config.VOLUME_KEY_TTL_HOURS * 3600)
    cursor = 0
    pruned = 0
    while True:
        cursor, keys = await redis_client.scan(cursor, match="vol:*", count=200)
        for key in keys:
            fields = await redis_client.hkeys(key)
            old_fields = [f for f in fields if f.isdigit() and int(f) < cutoff]
            if old_fields:
                await redis_client.hdel(key, *old_fields)
                pruned += len(old_fields)
        if cursor == 0:
            break
    if pruned:
        logger.info(f"Pruned {pruned} old buckets")


# ── Processing loop ──────────────────────────────────────────────────────

async def _process_batch(batch):
    global _processed, _unresolved

    ids = []
    for msg_id, tick in batch:
        ids.append(msg_id)
        exchange = tick.exchange
        pair = tick.pair
        data = tick.data

        coin_id = resolve_coin_id(exchange, pair)
        if not coin_id:
            _unresolved += 1
            continue

        try:
            price = float(data.get("price", 0))
            size = float(data.get("size", 0))
            side = data.get("side", "buy").lower()
        except (ValueError, TypeError):
            continue

        if price <= 0 or size <= 0:
            continue

        # Store base-asset quantity (not USD notional) so that
        # vol:ethereum = ETH traded, vol:bitcoin = BTC traded, etc.
        # This captures all pairs (USD, USDT, BTC-quoted) in the coin's own unit.
        volume = size
        minute_ts = int(tick.received_at) // config.VOLUME_BUCKET_SECONDS * config.VOLUME_BUCKET_SECONDS
        bucket_key = "b" if side == "buy" else "s"

        _accum[coin_id][minute_ts][bucket_key] += volume
        _accum[coin_id][minute_ts]["ex"].add(exchange)
        _processed += 1

    return ids


async def _run(redis_client: aioredis.Redis):
    global _consumer

    _consumer = StreamConsumer(
        redis_client=redis_client,
        stream_key=config.VOLUME_STREAM_KEY,
        group_name=config.VOLUME_CONSUMER_GROUP,
        consumer_name=config.VOLUME_CONSUMER_NAME,
        batch_size=200,
        block_ms=config.VOLUME_FLUSH_INTERVAL_MS,
    )
    await _consumer.setup()

    # Reclaim any pending messages from a previous crash
    pending = await _consumer.reclaim_pending()
    if pending:
        ids = await _process_batch(pending)
        await _consumer.ack(ids)

    last_flush = time.time()
    last_prune = time.time()
    flush_interval = config.VOLUME_FLUSH_INTERVAL_MS / 1000.0

    logger.info("Volume aggregator started — consuming from %s", config.VOLUME_STREAM_KEY)

    while True:
        batch = await _consumer.read_batch()
        if batch:
            ids = await _process_batch(batch)
            await _consumer.ack(ids)

        now = time.time()
        if now - last_flush >= flush_interval:
            await _flush_to_redis(redis_client)
            last_flush = now

        if now - last_prune >= config.VOLUME_PRUNE_INTERVAL_SECONDS:
            await _prune_old_buckets(redis_client)
            last_prune = now


# ── Health endpoint ──────────────────────────────────────────────────────

async def _health(_request):
    stats = _consumer.stats if _consumer else {}
    return web.json_response({
        "status": "ok",
        "processed": _processed,
        "unresolved": _unresolved,
        "consumer": stats,
    })


async def _start_health_server():
    app = web.Application()
    app.router.add_get("/health", _health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", config.HEALTH_PORT)
    await site.start()
    logger.info(f"Health server on :{config.HEALTH_PORT}")


# ── Entry point ──────────────────────────────────────────────────────────

async def main():
    _build_alias_map()
    redis_client = aioredis.from_url(config.REDIS_URL, decode_responses=True)
    await _start_health_server()
    await _run(redis_client)


if __name__ == "__main__":
    asyncio.run(main())
