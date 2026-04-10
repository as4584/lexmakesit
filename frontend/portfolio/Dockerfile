# Use Python base image
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Copy dependency list
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your code
COPY . .

# Create logs directory
RUN mkdir -p /app/logs && addgroup --system appgroup && adduser --system --ingroup appgroup appuser && chown -R appuser:appgroup /app

USER appuser

# Expose port
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health', timeout=3)"

# Start app with proper user permissions
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
