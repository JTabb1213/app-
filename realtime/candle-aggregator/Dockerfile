FROM python:3.12-slim

WORKDIR /app

COPY realtime/candle-aggregator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY realtime/candle-aggregator/ .

CMD ["python", "main.py"]
