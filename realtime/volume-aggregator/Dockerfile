FROM python:3.12-slim

WORKDIR /app

COPY realtime/volume-aggregator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY realtime/shared/ ./shared/
COPY realtime/volume-aggregator/ .
COPY data/ ./data/

CMD ["python", "main.py"]
