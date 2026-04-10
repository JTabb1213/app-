# Build from project root:
#   docker build -f realtime/collectors-secondary/Dockerfile -t collectors-secondary .

FROM python:3.12-slim

WORKDIR /app

# Dependencies first (cached layer)
COPY realtime/collectors-secondary/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Shared package
COPY realtime/shared/ ./shared/

# Service code
COPY realtime/collectors-secondary/ ./

# Alias data for symbol discovery
COPY data/coin_aliases.json /app/data/coin_aliases.json
ENV ALIAS_JSON_PATH=/app/data/coin_aliases.json

CMD ["python", "main.py"]
