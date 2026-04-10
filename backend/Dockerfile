FROM python:3.11-slim

WORKDIR /app

# Install system deps + Poetry (pinned for reproducibility)
RUN apt-get update && apt-get install -y libpq-dev gcc curl && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "poetry==1.8.3"

# Disable virtualenv creation — install directly into system Python
RUN poetry config virtualenvs.create false

# Copy dependency manifests first (layer cache: only invalidated on dep changes)
COPY ai_receptionist/pyproject.toml ai_receptionist/

# Install production dependencies only (no dev extras, no root package)
RUN cd ai_receptionist \
    && poetry install --no-root --only main --no-interaction

COPY . .

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8002/health', timeout=3)"

CMD ["uvicorn", "ai_receptionist.app.main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "4"]
