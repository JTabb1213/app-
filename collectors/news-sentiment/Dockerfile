FROM python:3.11-slim

WORKDIR /app

COPY collectors/news-sentiment/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY collectors/news-sentiment/config.py .
COPY collectors/news-sentiment/main.py .

CMD ["python", "main.py"]
