# Documentation Governance & Contributing

> **This file defines how documentation must be maintained to prevent drift, duplication, and stale content.**

---

## Core Principles

1. **Single Source of Truth** — Every concept has exactly ONE canonical document
2. **Co-locate with Code** — Update docs in the same commit as code changes
3. **No Orphans** — Every doc is linked from `docs/README.md`
4. **No Duplicates** — Never copy a doc to multiple locations; use links instead

---

## Documentation Ownership Map

| Area | Canonical Location | Owner |
|------|--------------------|-------|
| System architecture & call flow | `docs/backend/architecture.md` | Backend team |
| Critical config (ports, endpoints, Twilio) | `docs/backend/source-of-truth.md` | Backend team |
| Cost analysis & pricing | `docs/backend/cost-analysis.md` | Backend team |
| Performance / bug fixes | `docs/backend/performance.md` | Backend team |
| Evaluation system | `docs/backend/evaluation-system.md` | Backend team |
| Technical debt | `docs/backend/technical-debt.md` | Backend team |
| Calendar integration plan | `docs/backend/calendar-integration.md` | Backend team |
| Frontend apps (dashboard, portfolio) | `docs/frontend/` | Frontend team |
| Deployment & Docker | `docs/infra/deployment.md` | DevOps |
| CI/CD pipelines | `docs/infra/ci-cd.md` | DevOps |
| Server security | `docs/infra/server-hardening.md` | DevOps |
| Caddy / reverse proxy | `docs/infra/caddy-proxy.md` | DevOps |
| Monitoring & observability | `docs/infra/monitoring.md` | DevOps |
| Onboarding & pilot | `docs/etc/` | Business |
| Operations runbook | `docs/etc/operations.md` | Ops |
| Release planning | `docs/etc/release-plan.md` | PM |

---

## When to Update Docs

### Mandatory Updates (block the PR if missing)

| Code Change | Doc to Update |
|-------------|---------------|
| New/changed API endpoint | `backend/source-of-truth.md` + `backend/architecture.md` |
| Port, URL, or DNS change | `backend/source-of-truth.md` + `infra/caddy-proxy.md` |
| Docker config change | `infra/deployment.md` |
| New frontend app/page | `frontend/README.md` + relevant sub-doc |
| Cost-affecting change (model, provider) | `backend/cost-analysis.md` |
| Security change | `infra/server-hardening.md` |
| New CI/CD workflow | `infra/ci-cd.md` |
| Bug fix | `backend/performance.md` (add to changelog section) |
| New service/feature | `backend/architecture.md` |

### Optional Updates

- Refactoring that doesn't change behavior → update if it affects file structure
- Dependency updates → update if it changes deployment steps

---

## Agent Documentation Protocol

### For AI Agents (Antigravity, Copilot, etc.)

Every agent session that modifies code **MUST** follow this protocol:

1. **Before making changes**: Read the relevant doc in `docs/` to understand current state
2. **After making changes**: Update the affected doc(s) in the same commit
3. **Add a changelog entry**: Append to the "Change Log" section at the bottom of each affected doc
4. **Never create new docs outside `docs/`**: All docs go in `docs/{frontend,backend,infra,etc}/`

### Changelog Format

At the bottom of every doc, maintain a change log:

```markdown
---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-02-28 | Consolidated from scattered docs | Antigravity |
| YYYY-MM-DD | Description of change | Who |
```

---

## How to Add a New Document

1. Decide which folder it belongs in (`frontend/`, `backend/`, `infra/`, `etc/`)
2. Create the file with a kebab-case name (e.g., `new-feature-plan.md`)
3. Add a link to it in `docs/README.md` under the correct section
4. Add it to the ownership map in this file (`CONTRIBUTING.md`)
5. Include a Change Log section at the bottom

---

## How to Find Information

1. Start at `docs/README.md` — the master index
2. Use the "Quick Navigation" table to find the right doc
3. If you can't find it, it probably doesn't exist yet — create it!

---

## Anti-Patterns (DO NOT DO)

❌ Creating `.md` files in `backend/` root instead of `docs/backend/`
❌ Copying `OPERATIONS.md` into every service directory
❌ Creating `frontend/ai_receptionist/docs/` with duplicate content
❌ Having both `epismologicalCIagent.md` and `epistemologyciagent.md`
❌ Keeping the same doc in both `backend/` and `backend/docs/`

---

*This governance document was created 2026-02-28 during the Great Documentation Consolidation.*
