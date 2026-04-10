# Build from project root:
#   docker build -f realtime/live-price-ingestor/Dockerfile -t live-price-ingestor .

FROM python:3.12-slim

WORKDIR /app

# Dependencies first (cached layer)
COPY realtime/live-price-ingestor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Shared package
COPY realtime/shared/ ./shared/

# Service code
COPY realtime/live-price-ingestor/ ./

# Alias data for normalizer
COPY data/coin_aliases.json /app/data/coin_aliases.json
ENV ALIAS_JSON_PATH=/app/data/coin_aliases.json

CMD ["python", "main.py"]
