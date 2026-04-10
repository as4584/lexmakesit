# Monitoring & Observability

> Monitoring stack for the LexMakesIt infrastructure.

---

## Stack

| Component | Purpose | Location |
|-----------|---------|----------|
| **Loki** | Log aggregation | Docker container |
| **Promtail** | Log collection agent | Docker container |
| **Grafana** | Dashboards & visualization | `monitor.lexmakesit.com` (basic-auth) |

---

## Setup

```bash
cd infra/monitoring
docker compose up -d
```

Configuration: `infra/monitoring/promtail-config.yml`

---

## Auth Events

The FastAPI backend emits structured auth events to the `auth.events` logger. These are ingested by Loki and queryable in Grafana.

### Event Types

| Event | Level | When |
|-------|-------|------|
| `login_success` | INFO | Valid credentials, token issued |
| `login_failure` | WARNING | Wrong password |
| `login_locked` | WARNING | Account locked after repeated failures |
| `logout` | INFO | Token cookie cleared |
| `signup_success` | INFO | New user created |
| `dependency_degraded` | ERROR | Redis unavailable (auth proceeds stateless) |
| `dependency_recovered` | INFO | Redis reconnected |
| `readiness_failed` | ERROR | DB/Redis down at `/readiness` probe |

### Structured Log Format (when `STRUCTURED_LOGGING=true`)

```json
{
  "time": "2026-03-06T12:34:56.789Z",
  "level": "WARNING",
  "logger": "auth.events",
  "event": "login_failure",
  "email": "user@example.com",
  "latency_ms": 42,
  "request_id": "a1b2c3d4",
  "status_code": 401
}
```

Enable structured logging via Doppler: `STRUCTURED_LOGGING=true`.

### LogQL Queries (Grafana / Loki)

```logql
# All auth events
{container="ai_receptionist_active"} | json | logger = "auth.events"

# Failed logins in last hour
{container="ai_receptionist_active"} | json | logger = "auth.events" | event = "login_failure"

# Dependency degradation (triggers alert)
{container="ai_receptionist_active"} | json | event = "dependency_degraded"

# Login success rate
sum by (event) (
  count_over_time({container="ai_receptionist_active"} | json | logger = "auth.events" [1h])
)
```

### Recommended Alerts

| Condition | Threshold | Action |
|-----------|-----------|--------|
| `dependency_degraded` events | Any | Page on-call — Redis is down |
| `login_failure` rate | > 20/min | Investigate brute-force |
| `login_locked` events | > 5/min | Potential credential stuffing |
| `/readiness` returns 503 | Any | DB connectivity issue |

---

## Viewing Logs

### Via Grafana
Navigate to the Grafana dashboard and use LogQL queries:
```
{container="ai_receptionist_active"}
{container="portfolio-web-1"}
{container="antigravity_caddy"}
```

### Via CLI
```bash
# AI Receptionist logs
docker logs -f ai_receptionist_active

# Portfolio logs
docker logs -f portfolio-web-1

# Caddy logs
docker logs --tail 50 antigravity_caddy
```

---

## Health Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|------------------|
| `GET /health` | Liveness — always 200 | `{"status": "ok"}` |
| `GET /readiness` | Readiness — probes DB + Redis | `{"status": "ready", "checks": {...}}` or 503 |

Use `/readiness` for deploy gates and container health checks. Use `/health` for liveness probes only.

---

## Change Log

| Date | Change |
|------|--------|
| 2026-02-28 | Initial monitoring setup |
| 2026-03 | Auth events, structured logging, LogQL queries, alert table |


## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-02-28 | Consolidated from infra/monitoring/ and scattered docs | Antigravity |
