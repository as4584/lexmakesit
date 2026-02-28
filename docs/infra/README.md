# Infrastructure Documentation

> Documentation for servers, Docker, Caddy, CI/CD, monitoring, and security.

---

## Documents

| Document | Purpose |
|----------|---------|
| [deployment.md](deployment.md) | Docker deployment, server setup, deploy workflows |
| [caddy-proxy.md](caddy-proxy.md) | Caddy reverse proxy configuration |
| [server-hardening.md](server-hardening.md) | SSH, firewall, fail2ban, security |
| [monitoring.md](monitoring.md) | Loki, Promtail, Grafana monitoring stack |
| [ci-cd.md](ci-cd.md) | GitHub Actions pipelines, path-filtered triggers |

---

## Server Inventory

| Server | IP | Role | OS | SSH |
|--------|----|------|----|-----|
| Frontend | `104.236.100.245` | Portfolio, Dashboard, Caddy | Ubuntu | `ssh lex@104.236.100.245` |
| Backend | `174.138.67.169` | AI Receptionist API, DB, Redis | Ubuntu | `ssh lex@174.138.67.169` |

## Network Architecture

```
Internet
    │
    ▼
┌─────────────────────────────────────┐
│  104.236.100.245 (Frontend Server)  │
│                                     │
│  Caddy (antigravity_caddy)          │
│  ├─ lexmakesit.com → portfolio:8001│
│  ├─ dashboard.lexmakesit.com → ...  │
│  └─ receptionist.lexmakesit.com     │
│        → 174.138.67.169:8010        │
│                                     │
│  Docker Network: apps_antigravity_net│
│  ├─ portfolio-web-1 (:8001)         │
│  └─ Other frontend containers       │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  174.138.67.169 (Backend Server)    │
│                                     │
│  ai_receptionist_app (:8010)        │
│  PostgreSQL (:5432, internal)       │
│  Redis (:6379, internal)            │
│  Qdrant (:6333, internal)           │
└─────────────────────────────────────┘
```

---

## Quick Reference

### Restart services
```bash
# Portfolio
ssh lex@104.236.100.245 "cd ~/antigravity_bundle/apps/portfolio && docker compose up -d --force-recreate"

# AI Receptionist
ssh lex@174.138.67.169 "cd /home/lex/antigravity_bundle/apps && docker compose -f docker-compose.yml -f docker-compose.hotfix.yml restart ai_receptionist_app"

# Caddy reload
ssh lex@104.236.100.245 "docker exec antigravity_caddy caddy reload --config /etc/caddy/Caddyfile"
```

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-02-28 | Consolidated from infra/, frontend/lexmakesit-infra/, and scattered docs | Antigravity |
