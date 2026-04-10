# Caddy Reverse Proxy Configuration

> Caddy handles TLS termination, reverse proxying, and automatic HTTPS for all services.

---

## Location

- **Container**: `antigravity_caddy`
- **Server**: `lex@104.236.100.245`
- **Config file**: `/home/lex/antigravity_bundle/apps/Caddyfile`
- **Also in repo**: `infra/caddy/Caddyfile`

---

## Current Configuration

```
# Portfolio
lexmakesit.com, www.lexmakesit.com {
    reverse_proxy portfolio.internal:8001
}

# REST API + Auth (used by auth.lexmakesit.com SPA and direct API clients)
api.lexmakesit.com {
    reverse_proxy ai.internal:8002
}

# Auth Frontend SPA
auth.lexmakesit.com {
    reverse_proxy auth-frontend.internal:3000
}

# ⚠️ Twilio webhook — DO NOT rename; phone number +1 (229) 821-5986 is hardcoded here
receptionist.lexmakesit.com {
    reverse_proxy ai.internal:8002
}

# Inventory Manager
inventory.lexmakesit.com {
    reverse_proxy inventory.internal:8010
}

# Monitoring dashboard (basic-auth protected)
monitor.lexmakesit.com {
    basicauth * { ... }
    reverse_proxy grafana:3000
}
```

See `infra/caddy/Caddyfile` for the full config with security headers, rate limiting, and logging.

---

## Key Rules

⚠️ **DO NOT** add path rewrites or modify the proxy configuration without testing.

⚠️ **DO NOT** change or remove `receptionist.lexmakesit.com`. Twilio phone number +1 (229) 821-5986 is hardcoded to this domain. Renaming it requires a Twilio dashboard update.

⚠️ `api.lexmakesit.com` and `receptionist.lexmakesit.com` both proxy to `ai.internal:8002` (the same FastAPI backend). The split is intentional — it lets the Twilio webhook URL remain stable regardless of API surface changes.

- Caddy automatically manages **Let's Encrypt** certificates
- All domains resolve to `104.236.100.245`
- WebSocket connections are automatically proxied (needed for Twilio Media Streams)

---

## Reload Caddy

```bash
ssh lex@104.236.100.245 "docker exec antigravity_caddy caddy reload --config /etc/caddy/Caddyfile"
```

## View Caddy Logs

```bash
ssh lex@104.236.100.245 "docker logs --tail 50 antigravity_caddy"
```

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| 502 Bad Gateway | Backend container not running | Start the container, check `docker ps` |
| SSL errors | Certificate renewal failed | Check Caddy logs, ensure port 80/443 are open |
| WebSocket fails | Caddy not proxying WS | Caddy handles this automatically — check container network |
| CORS errors from `auth.lexmakesit.com` | Missing `CORS_ALLOWED_ORIGINS` env var | Ensure Doppler has `CORS_ALLOWED_ORIGINS=https://auth.lexmakesit.com,...` |

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-02-28 | Consolidated from infra/caddy/, backend/docs, and source-of-truth | Antigravity |
| 2026-03 | Added api.lexmakesit.com + auth.lexmakesit.com; documented Twilio constraint | Antigravity |
