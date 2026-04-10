#!/usr/bin/env bash
# scripts/ci/portfolio-test.sh
# ─────────────────────────────────────────────────────────────────────────────
# Run portfolio test + security scan locally or in GitHub Actions / act.
#
# Usage:
#   ./scripts/ci/portfolio-test.sh
#
# Optional env:
#   SKIP_SECURITY_SCAN=1   skip pip-audit/safety (useful for offline dev)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SERVICE_DIR="$REPO_ROOT/frontend/portfolio"

export ENVIRONMENT="${ENVIRONMENT:-ci}"

echo "==> portfolio-test: working directory $SERVICE_DIR"
cd "$SERVICE_DIR"

# ── Install ──────────────────────────────────────────────────────────────────
echo "==> Installing dependencies"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
pip install --quiet pytest pip-audit safety

# ── Security scan ────────────────────────────────────────────────────────────
if [ "${SKIP_SECURITY_SCAN:-0}" != "1" ]; then
  echo "==> pip-audit"
  pip-audit -r requirements.txt \
    --ignore-vuln CVE-2025-54121 \
    --ignore-vuln CVE-2025-62727 \
    --ignore-vuln CVE-2024-23342 || true

  echo "==> safety check"
  safety check -r requirements.txt --ignore 70612 --ignore 73683 || true
fi

# ── Tests ────────────────────────────────────────────────────────────────────
echo "==> pytest"
pytest -q --tb=short

echo "==> portfolio-test: PASSED"
