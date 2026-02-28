---
description: Update relevant documentation after code changes — prevents doc drift
---

# Update Documentation Workflow

// turbo-all

> **When to use**: After ANY code change that affects behavior, configuration, architecture, or deployment.
> This workflow ensures documentation stays in sync with code.

## Step 1: Identify Affected Docs

Based on your code changes, determine which docs need updating:

| What Changed | Doc to Update |
|-------------|---------------|
| API endpoints, routes, ports | `docs/backend/source-of-truth.md` |
| System architecture, call flow | `docs/backend/architecture.md` |
| Cost-affecting changes (model, provider) | `docs/backend/cost-analysis.md` |
| Bug fixes, performance changes | `docs/backend/performance.md` |
| Docker, compose, container config | `docs/infra/deployment.md` |
| Caddy, DNS, proxy changes | `docs/infra/caddy-proxy.md` |
| CI/CD pipeline changes | `docs/infra/ci-cd.md` |
| Security, firewall, SSH | `docs/infra/server-hardening.md` |
| Frontend app changes | `docs/frontend/README.md` |
| Onboarding, agreements | `docs/etc/onboarding.md` or `docs/etc/pilot-agreement.md` |
| Release process changes | `docs/etc/release-plan.md` |
| Operations procedures | `docs/etc/operations.md` |

## Step 2: Read the Current Doc

Before modifying, read the affected document to understand its current state:

```bash
cat docs/<area>/<document>.md
```

## Step 3: Update the Doc

Make the minimum necessary changes to keep the doc accurate. Follow these rules:

1. **Update facts** — Change any values, ports, URLs, commands that are now different
2. **Add new sections** — If your change introduces new concepts, add them
3. **Remove stale content** — If your change removes functionality, remove the doc section
4. **Update the Change Log** — Add a new row at the bottom of the Change Log table

### Change Log Entry Format
```markdown
| YYYY-MM-DD | Description of what changed | Your Name/Agent |
```

## Step 4: Verify No Duplicates

Ensure you did NOT:
- Create a new .md file outside of `docs/`
- Copy the doc to another location
- Create a file that overlaps with an existing doc

```bash
# Check for docs outside the docs/ folder
find . -name "*.md" -not -path "./docs/*" -not -path "./.git/*" -not -path "./.agent/*" -not -name "README.md" | head -20
```

## Step 5: Commit Together

Always commit doc updates in the **same commit** as the code change:

```bash
git add docs/<area>/<document>.md
git add <your-code-changes>
git commit -m "feat: <description> + update docs"
```
