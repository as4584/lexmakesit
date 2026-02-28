# Inventory Manager

Professional Inventory Management System with Lightspeed X-Series integration.

## Quick Start (Local Development)

1.  **Clone & Setup**:
    ```bash
    git clone <repo>
    cd inventory_manager
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Run Locally**:
    ```bash
    docker compose up -d
    ```
    Access at: http://localhost:8010

## Deployment

This repository uses **Blue/Green Deployment** via GitHub Actions.
- **Trigger**: Push to `main`.
- **CI/CD**: `.github/workflows/deploy.yml`.

### Secrets
Secrets are managed in GitHub Actions and injected into `/srv/env/inventory_manager/.env` on the server.

## Documentation
- [RELEASE PLAN](RELEASE_PLAN.md) - Deployment & Rollback steps.
- [OPERATIONS](OPERATIONS.md) - Debugging & Maintenance.
- [SECURITY](SECURITY.md) - Security policies.