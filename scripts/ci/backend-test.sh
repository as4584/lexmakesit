#!/usr/bin/env bash
# scripts/ci/backend-test.sh
# ─────────────────────────────────────────────────────────────────────────────
# Run backend lint + test locally or in GitHub Actions / act with identical
# behaviour.  Works from any CWD — it resolves paths relative to the repo root.
#
# Usage:
#   ./scripts/ci/backend-test.sh
#
# Required env (same variables used by GitHub Actions workflow):
#   JWT_SECRET_KEY      — any non-empty string for tests
#   DATABASE_URL        — postgres or sqlite (optional; SQLite used if absent)
#   REDIS_URL           — redis URL (optional; stateless mode if absent)
#   ENVIRONMENT         — defaults to "ci"
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SERVICE_DIR="$REPO_ROOT/backend/ai_receptionist"

export JWT_SECRET_KEY="${JWT_SECRET_KEY:-ci-local-secret}"
export ENVIRONMENT="${ENVIRONMENT:-ci}"
export STRUCTURED_LOGGING="${STRUCTURED_LOGGING:-true}"

echo "==> backend-test: working directory $SERVICE_DIR"
cd "$SERVICE_DIR"

# ── Install ──────────────────────────────────────────────────────────────────
echo "==> Installing dependencies via Poetry"
pip install --quiet poetry
poetry install --no-root

# ── Lint ─────────────────────────────────────────────────────────────────────
echo "==> ruff lint"
poetry run ruff check .

echo "==> black format check"
poetry run black --check .

# ── Tests ────────────────────────────────────────────────────────────────────
echo "==> pytest"
poetry run pytest -q --tb=short

echo "==> backend-test: PASSED"
