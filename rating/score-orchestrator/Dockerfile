FROM python:3.12-slim

WORKDIR /app

# Install dependencies for orchestrator + all collectors
COPY score-orchestrator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full rating/ directory so all collector modules are importable
COPY . /rating
WORKDIR /rating/score-orchestrator

# Copy the project-wide coin aliases file (lives outside rating/ in the repo)
# The build context for this service is ./rating, so the file must be passed
# in via a volume or baked in at build time from the repo root.
# We set a well-known path so coin_registry.py can find it reliably.
ENV COIN_ALIASES_FILE=/rating/data/coin_aliases.json

# Make the rating root importable so `from writers import ...` and
# `from collectors import ...` resolve correctly
ENV PYTHONPATH=/rating

CMD ["python", "main.py"]
