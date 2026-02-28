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
lexmakesit.com {
    reverse_proxy portfolio-web-1:8000
}

dashboard.lexmakesit.com {
    reverse_proxy dashboard-app:3000
}

receptionist.lexmakesit.com {
    reverse_proxy ai_receptionist_app:8010
}
```

---

## Key Rules

⚠️ **DO NOT** add path rewrites or modify the proxy configuration without testing.

⚠️ **DO NOT** change the `receptionist.lexmakesit.com` proxy target. Twilio depends on it.

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

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-02-28 | Consolidated from infra/caddy/, backend/docs, and source-of-truth | Antigravity |
