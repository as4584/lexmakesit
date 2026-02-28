# AI Receptionist

Intelligent Voice Receptionist powered by OpenAI, Twilio, and Qdrant.

## Quick Start (Local Development)

1.  **Clone & Setup**:
    ```bash
    git clone <repo>
    cd ai_receptionist
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Start Dependencies**:
    ```bash
    docker compose -f docker-compose.dev.yml up -d
    ```

3.  **Run App**:
    ```bash
    uvicorn main:app --reload --port 8002
    ```

## Deployment

This repository uses **Blue/Green Deployment** via GitHub Actions.
- **Trigger**: Push to `main`.
- **CI/CD**: `.github/workflows/deploy.yml`.

### Secrets
Secrets are managed in GitHub Actions and injected into `/srv/env/ai_receptionist/.env` on the server.

## Documentation
- [RELEASE PLAN](RELEASE_PLAN.md) - Deployment & Rollback steps.
- [OPERATIONS](OPERATIONS.md) - Debugging & Maintenance.
- [SECURITY](SECURITY.md) - Security policies.
