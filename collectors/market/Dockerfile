FROM python:3.11-slim

WORKDIR /app

COPY collectors/market/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY collectors/market/config.py .
COPY collectors/market/main.py .

CMD ["python", "main.py"]
