# ─────────────────────────────────────────────────────────────
# Collectors-Primary (Kraken, Coinbase, Binance)
# ─────────────────────────────────────────────────────────────
# Build context: project root
#   docker build -f realtime/collectors-primary/Dockerfile -t collectors-primary .
# ─────────────────────────────────────────────────────────────

FROM python:3.12-slim

WORKDIR /app

COPY realtime/collectors-primary/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Shared code (models, stream, base exchange)
COPY realtime/shared/ ./shared/

# Service code
COPY realtime/collectors-primary/ ./

# Alias file for symbol discovery
COPY data/coin_aliases.json /app/data/coin_aliases.json
ENV ALIAS_JSON_PATH=/app/data/coin_aliases.json

ENV PORT=8080
EXPOSE 8080

CMD ["python", "main.py"]
