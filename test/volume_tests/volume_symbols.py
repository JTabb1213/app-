#!/usr/bin/env python3
"""
Volume / ticker test symbol helpers.

Loads all canonical coin IDs from data/coin_aliases.json and builds
exchange-specific symbol/pair names for test scripts.

Quote conventions used:
  Binance   — USDT  (e.g. ETHUSDT)
  Kraken    — USD   (e.g. ETH/USD  — USD is more broadly supported than USDT)
  Coinbase  — USD   (e.g. ETH-USD  — Coinbase doesn't offer USDT pairs)
  OKX       — USDT  (e.g. ETH-USDT)
  Gate.io   — USDT  (e.g. ETH_USDT)
  Bybit     — USDT  (e.g. ETHUSDT)
  Pionex    — USDT  (e.g. ETH_USDT)
"""

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
COIN_ALIASES_PATH = ROOT / "data" / "coin_aliases.json"

_ASSETS: dict | None = None


def _load_assets() -> dict:
    global _ASSETS
    if _ASSETS is None:
        with open(COIN_ALIASES_PATH, "r", encoding="utf-8") as f:
            _ASSETS = json.load(f)["assets"]
    return _ASSETS


def _exchange_symbol(canonical_id: str, exchange: str) -> str | None:
    """Return the exchange-specific ticker for a canonical coin ID, or None."""
    entry = _load_assets().get(canonical_id, {})
    return entry.get("exchange_symbols", {}).get(exchange)


# ---------------------------------------------------------------------------
# Per-exchange pair builders — USDT or USD only
# ---------------------------------------------------------------------------

def binance_symbols() -> list[str]:
    """ETHUSDT-style pairs for all coins in coin_aliases.json."""
    pairs = []
    for cid, entry in _load_assets().items():
        sym = entry.get("exchange_symbols", {}).get("binance")
        if sym:
            pairs.append(f"{sym}USDT")
    return sorted(pairs)


def kraken_pairs() -> list[str]:
    """ETH/USD-style pairs for all coins in coin_aliases.json."""
    pairs = []
    for cid, entry in _load_assets().items():
        sym = entry.get("exchange_symbols", {}).get("kraken")
        if sym:
            pairs.append(f"{sym}/USD")
    return sorted(pairs)


def coinbase_products() -> list[str]:
    """ETH-USD-style products for all coins in coin_aliases.json."""
    pairs = []
    for cid, entry in _load_assets().items():
        sym = entry.get("exchange_symbols", {}).get("coinbase")
        if sym:
            pairs.append(f"{sym}-USD")
    return sorted(pairs)


def okx_pairs() -> list[str]:
    """ETH-USDT-style instIds for all coins in coin_aliases.json."""
    pairs = []
    for cid, entry in _load_assets().items():
        sym = entry.get("exchange_symbols", {}).get("okx")
        if sym:
            pairs.append(f"{sym}-USDT")
    return sorted(pairs)


def gateio_pairs() -> list[str]:
    """ETH_USDT-style pairs for all coins in coin_aliases.json."""
    pairs = []
    for cid, entry in _load_assets().items():
        sym = entry.get("exchange_symbols", {}).get("gateio")
        if sym:
            pairs.append(f"{sym}_USDT")
    return sorted(pairs)


def bybit_symbols() -> list[str]:
    """ETHUSDT-style pairs for all coins in coin_aliases.json."""
    pairs = []
    for cid, entry in _load_assets().items():
        sym = entry.get("exchange_symbols", {}).get("bybit")
        if sym:
            pairs.append(f"{sym}USDT")
    return sorted(pairs)


def pionex_pairs() -> list[str]:
    """ETH_USDT-style pairs for all coins in coin_aliases.json."""
    pairs = []
    for cid, entry in _load_assets().items():
        sym = entry.get("exchange_symbols", {}).get("pionex")
        if sym:
            pairs.append(f"{sym}_USDT")
    return sorted(pairs)
