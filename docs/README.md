# LexMakesIt — Documentation Hub

> **Single source of truth for all project documentation.**
> Every doc lives here. If it's not in `docs/`, it doesn't exist.

---

## Directory Structure

| Folder | Scope | Contents |
|--------|-------|----------|
| [`frontend/`](frontend/) | Dashboard, Portfolio, Inventory Manager | UI architecture, components, deployment |
| [`backend/`](backend/) | FastAPI AI Receptionist API | Architecture, endpoints, cost analysis, performance |
| [`infra/`](infra/) | Servers, Docker, Caddy, CI/CD | Deployment, hardening, monitoring, proxy config |
| [`etc/`](etc/) | Business & operations | Onboarding, pilot agreements, release plan, operations |

---

## Quick Navigation

### I need to…

| Task | Document |
|------|----------|
| **Understand the system** | [backend/architecture.md](backend/architecture.md) |
| **Deploy changes** | [infra/deployment.md](infra/deployment.md) |
| **Debug a call issue** | [backend/source-of-truth.md](backend/source-of-truth.md) |
| **Check costs** | [backend/cost-analysis.md](backend/cost-analysis.md) |
| **Onboard a new client** | [etc/onboarding.md](etc/onboarding.md) |
| **Understand CI/CD** | [infra/ci-cd.md](infra/ci-cd.md) |
| **Harden the server** | [infra/server-hardening.md](infra/server-hardening.md) |
| **Update the frontend** | [frontend/README.md](frontend/README.md) |

---

## Documentation Governance

> See [CONTRIBUTING.md](CONTRIBUTING.md) for the complete governance system.

### Rules

1. **One canonical location** — Every piece of information lives in exactly one file
2. **No duplicates** — Don't copy docs into service directories; link here instead
3. **Update on change** — When you change code, update the matching doc in the same PR/commit
4. **Agent auto-update** — AI agents must follow the `docs-update-protocol` workflow

### How Agents Must Update Docs

Every AI agent session that modifies code **must** also update the relevant docs.
See the `update-docs` workflow at `.agent/workflows/update-docs.md` for the exact protocol.

---

## Server Reference

| Server | IP | Role | SSH |
|--------|----|------|-----|
| Frontend | `104.236.100.245` | Portfolio, Dashboard, Caddy | `ssh lex@104.236.100.245` |
| Backend | `174.138.67.169` | AI Receptionist API, DB | `ssh lex@174.138.67.169` |

---

*Last updated: 2026-02-28*
