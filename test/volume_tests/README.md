# Volume Subscription Test Scripts

This folder contains simple websocket test scripts for Gate.io, OKX, MEXC, and Pionex.
Each script connects to the exchange's public websocket endpoint, subscribes to a trade-related feed, and prints raw responses to the terminal.

## Usage

From the project root:

```bash
python tools/volume_tests/test_gateio_volume.py
python tools/volume_tests/test_okx_volume.py
python tools/volume_tests/test_mexc_volume.py
python tools/volume_tests/test_pionex_volume.py
python tools/volume_tests/test_bybit_volume.py
python tools/volume_tests/test_kraken_volume.py
python tools/volume_tests/test_coinbase_volume.py
python tools/volume_tests/test_binance_volume.py
```

## Notes

- These scripts are designed to show raw trade data for buy/sell volume analysis.
- If `websockets` is not installed, run:

```bash
pip install websockets
```
