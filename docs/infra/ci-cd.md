# CI/CD Architecture

> GitHub Actions pipelines, deployment triggers, and testing automation.

---

## Monorepo Structure

Root-level workflows fire on matching path changes. Each service has a dedicated pipeline.

| Service | Path Trigger | Workflow |
|---------|-------------|----------|
| Backend (AI Receptionist) | `backend/**` | `.github/workflows/ci-backend.yml` |
| Portfolio | `frontend/portfolio/**` | `.github/workflows/ci-portfolio.yml` |
| Infrastructure | `infra/**` | — (manual) |

> **Historical note:** Prior to 2026-03, workflow files lived inside service subdirectories (`backend/.github/workflows/`). They were inaccessible to GitHub Actions. Root-level workflows were added to fix this.

---

## Pipeline Stages

Every CI run follows four gates:

```
push / PR
    │
    ▼
┌───────────────────────────────┐
│  1. TEST                      │
│  • Postgres 15 + Redis 7      │
│    (service containers)       │
│  • poetry install             │
│  • ruff + black               │
│  • pytest -q                  │
└───────────────┬───────────────┘
                │ (main branch only)
                ▼
┌───────────────────────────────┐
│  2. IMAGE                     │
│  • docker build               │
│  • smoke: /health + /readiness│
│  • push to GHCR               │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│  3. DEPLOY                    │
│  • SSH to DigitalOcean server │
│  • doppler secrets download   │
│  • docker run (blue slot)     │
│  • 3 × /readiness == 200      │
│  • swap slot, retire old      │
└───────────────────────────────┘
```

---

## Secrets Management — Doppler

All runtime secrets are managed in [Doppler](https://www.doppler.com). A single `DOPPLER_TOKEN` GitHub Secret (service token) replaces all previous `*_ENV` blob secrets.

| GitHub Secret | Purpose |
|---------------|---------|
| `DOPPLER_TOKEN` | Service token — Doppler fetches all app secrets at deploy time |
| `SERVER_HOST` | DigitalOcean droplet IP |
| `SERVER_USER` | SSH login user |
| `SSH_PRIVATE_KEY` | Deploy key |
| `GITHUB_TOKEN` | GHCR read/write (built-in) |

**Doppler stores** (keep GHCR_TOKEN, DB credentials, JWT secret, OpenAI key, Twilio credentials here, not in GitHub Secrets).

### How secrets reach the container

```bash
# On the server during deploy:
doppler secrets download --format env --no-file > /tmp/run.env
docker run --env-file /tmp/run.env ... IMAGE
rm /tmp/run.env
```

The env file is written to a tmpfs path with `chmod 600` and deleted immediately after `docker run` returns.

---

## Blue/Green Deployment

- **Readiness gate**: 3 consecutive `HTTP 200` responses at `/readiness` (not `/health`)
- `/readiness` probes PostgreSQL + Redis; returns 503 if either is down
- If the gate fails, the new slot is removed and the old slot remains active
- Slot naming: `ai_receptionist_blue` / `ai_receptionist_green` (same for portfolio)

---

## Local Parity with `act`

Run CI locally using [act](https://github.com/nektos/act):

```bash
# Install act, then run the backend test job
act push -W .github/workflows/ci-backend.yml -j test
```

Config: `.actrc` (runner image, secrets file path, reuse containers)
Secrets: Copy `.act/secrets.example` → `.act/secrets` and fill in `DOPPLER_TOKEN`.

---

## Deployment Safety Contract

Before any push, ALL must pass:
- ✅ Tests (`pytest` — 100% green)
- ✅ Linting (`ruff check .` + `black --check .`)
- ✅ Docker build (no failing layers)
- ✅ Smoke test (`/health` ok + `/readiness` 200 or 503)
- ✅ Readiness gate (3 consecutive passes before slot promotion)

### Forbidden Actions
- ❌ Push with failing tests
- ❌ Disable linting to bypass errors
- ❌ Push `--no-verify` to skip pre-push checks
- ❌ Deploy unreviewed code to production

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-02-28 | Initial CI/CD strategy | Antigravity |
| 2026-03 | Root-level workflows, Doppler secrets, readiness gate at `/readiness` | Antigravity |


| Date | Change | Author |
|------|--------|--------|
| 2026-02-28 | Consolidated from frontend/docs/ci-architecture.md, deployment.md, RELEASE_PLAN.md | Antigravity |
