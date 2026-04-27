# ─────────────────────────────────────────────────────────────
# Trade Collectors-Primary (Kraken, Coinbase, Binance) — Trades
# ─────────────────────────────────────────────────────────────
# Build context: project root
#   docker build -f realtime/trade-collectors-primary/Dockerfile -t trade-collectors-primary .
# ─────────────────────────────────────────────────────────────

FROM python:3.12-slim

WORKDIR /app

COPY realtime/trade-collectors-primary/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY realtime/shared/ ./shared/
COPY realtime/trade-collectors-primary/ ./
COPY data/coin_aliases.json /app/data/coin_aliases.json
ENV ALIAS_JSON_PATH=/app/data/coin_aliases.json

ENV PORT=8080
EXPOSE 8080

CMD ["python", "main.py"]
