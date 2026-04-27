FROM python:3.12-slim

WORKDIR /app

COPY realtime/trade-collectors-secondary/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY realtime/shared/ ./shared/
COPY realtime/trade-collectors-secondary/ .
COPY data/coin_aliases.json ./data/coin_aliases.json

CMD ["python", "main.py"]
