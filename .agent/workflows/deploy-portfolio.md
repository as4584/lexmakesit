---
description: Rebuild and deploy the portfolio web container with latest changes
---

# Portfolio Deployment Workflow

// turbo-all

## Server Info
- **Frontend server**: `lex@104.236.100.245`
- **Backend server**: `lex@174.138.67.169` (DO NOT TOUCH for portfolio deploys)
- **Portfolio path**: `~/antigravity_bundle/apps/portfolio`
- **Container name**: `portfolio-web-1` (via docker compose)
- **Port**: 8001 → 8000 inside container
- **Caddy container**: `antigravity_caddy`

## Pre-Deployment Checks
1. Run local tests to verify changes work
   ```bash
   cd frontend/portfolio && python -m pytest tests/ -v
   ```

2. Lint check for any syntax errors
   ```bash
   cd frontend/portfolio && python -m py_compile main.py
   ```

## Deployment Steps

3. Copy updated templates to server
   ```bash
   scp -r frontend/portfolio/templates/ lex@104.236.100.245:~/antigravity_bundle/apps/portfolio/templates/
   ```

4. Copy updated static files (if changed)
   ```bash
   scp -r frontend/portfolio/static/css lex@104.236.100.245:~/antigravity_bundle/apps/portfolio/static/
   scp -r frontend/portfolio/static/js lex@104.236.100.245:~/antigravity_bundle/apps/portfolio/static/
   ```

5. Copy main.py if changed
   ```bash
   scp frontend/portfolio/main.py lex@104.236.100.245:~/antigravity_bundle/apps/portfolio/main.py
   ```

6. SSH into server and rebuild container
   ```bash
   ssh lex@104.236.100.245 "cd ~/antigravity_bundle/apps/portfolio && docker build -t portfolio_web:latest . && IMAGE_NAME=portfolio_web IMAGE_TAG=latest docker compose up -d --force-recreate"
   ```

7. Verify health check
   ```bash
   ssh lex@104.236.100.245 "sleep 5 && curl -s http://localhost:8001/api/health"
   ```

8. Reload Caddy to clear any cache
   ```bash
   ssh lex@104.236.100.245 "docker exec antigravity_caddy caddy reload --config /etc/caddy/Caddyfile"
   ```

## Post-Deployment Verification

9. Check live site via curl
   ```bash
   curl -s https://lexmakesit.com/api/health
   ```

## Rollback (if needed)
If deployment fails, revert to previous golden commit locally and re-deploy:
```bash
cd frontend/portfolio && git log --oneline -5
# Find the last known good commit and:
git reset --hard <golden-commit-hash>
# Then re-run steps 3-8
```
