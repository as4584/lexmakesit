# Release Plan - Inventory Manager

## Pre-Deployment Checklist
- [ ] **Tests**: Ensure all unit tests pass locally (`pytest`).
- [ ] **Security**: Run `pip-audit` and `safety check` locally.
- [ ] **Secrets**: Verify any new environment variables are added to GitHub Secrets (`INVENTORY_ENV`).

## Deployment Architecture
- **Strategy**: Blue/Green Deployment.
- **Orchestration**: GitHub Actions -> SSH -> Docker Compose.
- **Traffic Switching**: Caddy (Global) -> `inventory.internal:8010` (Load Balanced).
- **Readiness Gate**: New container must pass 3 consecutive health checks at `/health`.

## Rollback Steps
**Automatic**: The CI/CD pipeline will automatically stop the new container if readiness checks fail.

**Manual Rollback**:
1.  SSH into the server.
2.  Identify the running "Green" container.
3.  Identify the stopped "Blue" container.
4.  Start the old container:
    ```bash
    cd /srv/inventory_manager
    docker compose -p inventory_manager-blue up -d
    ```
5.  Stop the new container:
    ```bash
    docker compose -p inventory_manager-green down
    ```

## Validation
- **Health Check**: `curl https://inventory.lexmakesit.com/health`
- **Logs**: Check Grafana or `docker logs inventory_manager-green-app-1`.
