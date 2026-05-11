FROM python:3.12-slim

WORKDIR /app

# Install dependencies for orchestrator + all collectors
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full rating/ directory so all collector modules are importable
COPY .. /rating
WORKDIR /rating/score-orchestrator

CMD ["python", "main.py"]
