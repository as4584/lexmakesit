# CI/CD Architecture

> GitHub Actions pipelines, deployment triggers, and testing automation.

---

## Monorepo Structure

The repository contains multiple services, each with its own CI lifecycle:

| Service | Path | Trigger | Pipeline |
|---------|------|---------|----------|
| Portfolio | `frontend/portfolio/` | `portfolio/**` | `deploy-portfolio.yml` |
| Inventory Manager | `frontend/inventory_manager/` | `inventory_manager/**` | `deploy-inventory.yml` |
| AI Receptionist | `backend/` | `backend/**` | — (manual deploy) |
| Infrastructure | `infra/` | — | — |

---

## Workflow Strategy

**Path-Filtered Triggers** — Each service pipeline fires only when its own files change.

- **Global Guardian**: Runs on ALL pushes. Checks repo health, linting, security policies.
- **Service Pipelines**: Trigger only for matching path changes.

---

## Deployment Chain

1. **Test**: Unit tests (`pytest`) + Static Analysis (`ruff`, `mypy`)
2. **Audit**: Security scanning (`pip-audit`, `safety`)
3. **Build**: Docker image creation (`docker build`)
4. **Push**: Upload to GHCR (`ghcr.io`) (if configured)
5. **Deploy**: SSH into DigitalOcean → `docker compose pull` → `docker compose up`

---

## Security Architecture

- **Secrets Management**: All sensitive data via GitHub Secrets (`*_ENV`, `SSH_KEY`)
- **Vulnerability Management**:
  - High/Critical CVEs block deployment
  - Low/Medium CVEs may be allowed with documented justification
- **Network**: All services behind Caddy with automatic HTTPS

---

## Deployment Safety Contract

> See `frontend/docs/deployment.md` for the full Deployment Guardian contract

### Push Protection Rules

Before any push, ALL of the following must pass:
- ✅ Tests (`pytest` — 100% green)
- ✅ Linting (`ruff check .` + `black --check .`)
- ✅ Docker build (no failing layers)
- ✅ Docker health (container reaches "healthy")
- ✅ No uncommitted migrations
- ✅ No secrets in staged files

### Forbidden Actions
- ❌ Push with failing tests
- ❌ Disable linting to bypass errors
- ❌ Push directly to production branches
- ❌ Deploy unreviewed code

---

## Blue/Green Deployment (AI Receptionist)

- **Strategy**: Blue/Green with health gate
- **Orchestration**: GitHub Actions → SSH → Docker Compose
- **Traffic Switching**: Caddy → `ai.internal:8002`
- **Readiness Gate**: 3 consecutive health checks at `/health`

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-02-28 | Consolidated from frontend/docs/ci-architecture.md, deployment.md, RELEASE_PLAN.md | Antigravity |
