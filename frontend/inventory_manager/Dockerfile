# Inventory Manager - Production Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Configure Poetry to not create a virtual environment in Docker
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-root --only main

# Copy application files
COPY . .

# Set Python path to include src/
ENV PYTHONPATH=/app/src

# Set environment variables for production
ENV FLASK_ENV=production
ENV PORT=8010
ENV DEMO_MODE=false

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Expose port
EXPOSE 8010

# Use gunicorn with proper workers and proxy headers
CMD ["poetry", "run", "gunicorn", "-b", "0.0.0.0:8010", "-w", "2", "--proxy-headers", "--chdir", "/app/scripts", "run_local:app"]