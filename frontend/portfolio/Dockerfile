# Pin the production base image for repeatable recovery builds.
FROM python:3.11-alpine@sha256:0d55920083f1ce1e38ac292e2772f924b4f8bb4188d336c79bf66963039e6146 AS runtime

ARG VCS_REF=unknown
LABEL org.opencontainers.image.source="https://github.com/as4584/lexmakesit" \
      org.opencontainers.image.revision="$VCS_REF"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apk upgrade --no-cache

# Set work directory
WORKDIR /app

# Copy dependency list
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create the runtime identity before copying application files.
RUN addgroup -S appgroup && adduser -S -G appgroup appuser

# Copy only files required by the running portfolio. Keeping the allowlist here
# prevents documentation, CI fixtures, and dormant deployment scripts from
# becoming part of the production attack surface.
COPY --chown=appuser:appgroup main.py ./main.py
COPY --chown=appuser:appgroup storage.py ./storage.py
COPY --chown=appuser:appgroup abuse_guard.py ./abuse_guard.py
COPY --chown=appuser:appgroup static ./static
COPY --chown=appuser:appgroup templates ./templates
COPY --chown=appuser:appgroup docker/entrypoint.sh ./docker/entrypoint.sh

RUN mkdir -p /app/logs && \
    chown -R appuser:appgroup /app && \
    chmod 0555 /app/docker/entrypoint.sh

USER appuser

# Expose port
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health', timeout=3)"

# Start app with proper user permissions
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Test tooling is intentionally excluded from the production image.
FROM runtime AS test
USER root
COPY requirements-dev.txt /app/requirements-dev.txt
RUN pip install --no-cache-dir -r /app/requirements-dev.txt
USER appuser

FROM runtime AS production
USER root
RUN python -m pip uninstall -y jaraco.context wheel setuptools pip
USER appuser
