# ── Stage 1: build/install dependencies ──────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install dependencies into a separate prefix so we can copy them cleanly
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: lean runtime image ───────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY backend/ .

# Copy shared data directory — resolver.py navigates ../../../data from
# services/alias/, so with WORKDIR=/app the file must be at /app/data/
# (three levels up from /app/services/alias/ is still /app/).
COPY data/ ./data/

# Cloud Run injects $PORT at runtime (default 8080).
# Gunicorn picks it up via the shell form of CMD.
ENV PORT=8080

# Use gunicorn for production (add it to requirements.txt too – see note below)
CMD exec gunicorn --bind "0.0.0.0:${PORT}" --workers 2 --threads 4 --timeout 60 "app:create_app()"
