# Monitoring & Observability

> Monitoring stack for the LexMakesIt infrastructure.

---

## Stack

| Component | Purpose | Location |
|-----------|---------|----------|
| **Loki** | Log aggregation | Docker container |
| **Promtail** | Log collection agent | Docker container |
| **Grafana** | Dashboards & visualization | Docker container |

---

## Setup

```bash
cd infra/monitoring
docker compose up -d
```

Configuration: `infra/monitoring/promtail-config.yml`

---

## Viewing Logs

### Via Grafana
Navigate to the Grafana dashboard and use LogQL queries:
```
{container="ai_receptionist-green-app-1"}
{container="portfolio-web-1"}
{container="antigravity_caddy"}
```

### Via CLI
```bash
# AI Receptionist logs
docker logs -f ai_receptionist_app

# Portfolio logs
docker logs -f portfolio-web-1

# Caddy logs
docker logs --tail 50 antigravity_caddy
```

---

## Alerting (Future)

- Set up Grafana alerts for:
  - Container restarts
  - 5xx error rate > threshold
  - Response latency > 5s
  - Disk usage > 80%

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-02-28 | Consolidated from infra/monitoring/ and scattered docs | Antigravity |
