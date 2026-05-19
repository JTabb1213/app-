FROM python:3.11-slim

WORKDIR /app

COPY collectors/news/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY collectors/news/config.py .
COPY collectors/news/main.py .

CMD ["python", "main.py"]
