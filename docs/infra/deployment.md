# Deployment Guide

> How to deploy all services in the LexMakesIt ecosystem.

---

## Quick Deploy Commands

### Portfolio (lexmakesit.com)

Use the `/deploy-portfolio` workflow. Summary:

```bash
# 1. Copy files to server
scp -r frontend/portfolio/templates/ lex@104.236.100.245:~/antigravity_bundle/apps/portfolio/templates/
scp -r frontend/portfolio/static/css lex@104.236.100.245:~/antigravity_bundle/apps/portfolio/static/
scp -r frontend/portfolio/static/js lex@104.236.100.245:~/antigravity_bundle/apps/portfolio/static/
scp frontend/portfolio/main.py lex@104.236.100.245:~/antigravity_bundle/apps/portfolio/main.py

# 2. Rebuild container
ssh lex@104.236.100.245 "cd ~/antigravity_bundle/apps/portfolio && docker build -t portfolio_web:latest . && IMAGE_NAME=portfolio_web IMAGE_TAG=latest docker compose up -d --force-recreate"

# 3. Verify
ssh lex@104.236.100.245 "sleep 5 && curl -s http://localhost:8001/api/health"

# 4. Reload Caddy
ssh lex@104.236.100.245 "docker exec antigravity_caddy caddy reload --config /etc/caddy/Caddyfile"

# 5. Check live
curl -s https://lexmakesit.com/api/health
```

### AI Receptionist (receptionist.lexmakesit.com)

```bash
# Restart the app
ssh lex@174.138.67.169 "cd /home/lex/antigravity_bundle/apps && docker compose -f docker-compose.yml -f docker-compose.hotfix.yml restart ai_receptionist_app"

# View logs
ssh lex@174.138.67.169 "docker logs --tail 100 ai_receptionist_app"

# Copy updated file (hotfix)
scp backend/ai_receptionist/api/realtime.py lex@174.138.67.169:/home/lex/antigravity_bundle/apps/ai_receptionist_new/ai_receptionist/api/realtime.py

# Health check
curl -s https://receptionist.lexmakesit.com/health
```

---

## Docker Architecture

### Frontend Server (104.236.100.245)

| Container | Image | Port | Network |
|-----------|-------|------|---------|
| `portfolio-web-1` | `portfolio_web:latest` | 8001 → 8000 | `apps_antigravity_net` |
| `antigravity_caddy` | Caddy | 80, 443 | `apps_antigravity_net` |

### Backend Server (174.138.67.169)

| Container | Image | Port | Network |
|-----------|-------|------|---------|
| `ai_receptionist_app` | Custom | 8010 | `apps_antigravity_net` |
| PostgreSQL | postgres:15 | 5432 (internal) | `apps_antigravity_net` |
| Redis | redis:7 | 6379 (internal) | `apps_antigravity_net` |
| Qdrant | qdrant | 6333 (internal) | `apps_antigravity_net` |

### Docker Compose Files (Backend)
- `docker-compose.yml` — Base configuration
- `docker-compose.hotfix.yml` — Override for mounting local code
- `docker-compose.prod.yml` — Full production stack
- `docker-compose.dev.yml` — Development environment

### Startup Command (AI Receptionist)
```bash
pip install twilio aiohttp && uvicorn ai_receptionist.app.main:app --host 0.0.0.0 --port 8010 --workers 4
```

---

## Rollback Procedures

### Portfolio
```bash
cd frontend/portfolio && git log --oneline -5
git reset --hard <golden-commit-hash>
# Re-run deployment steps
```

### AI Receptionist (Blue/Green)
```bash
# Start old container
docker compose -f docker-compose.prod.yml -p ai_receptionist-blue up -d
# Stop new container
docker compose -p ai_receptionist-green down
# Database rollback (if migrations ran)
docker exec ai_receptionist-blue-app-1 alembic downgrade -1
```

---

## Environment Variables

Located at: `/srv/env/ai_receptionist/.env` (permissions: `600 root:root`)

See [/docs/backend/source-of-truth.md](/docs/backend/source-of-truth.md) for the full list.

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-02-28 | Consolidated from deploy-portfolio workflow, OPERATIONS.md, RELEASE_PLAN.md, deployment.md | Antigravity |
