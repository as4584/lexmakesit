# Security Sprints + Codex Implementation Spec

**Date:** 2026-03-06  
**Owner:** Platform Security  
**Status:** Sprint 4 Implemented (Production Verified)

---

## Scope
Implement Kimi's security hardening fixes in production-safe order:
1. Secrets/defaults and middleware hardening
2. Shared rate limiting and container hardening
3. Encryption migration and key hygiene
4. Auth lifecycle hardening + ops verification

---

## Sprint 1 (Emergency) — Secrets + Defaults

### Objectives
- Remove insecure secret fallbacks
- Tighten JWT signing config and token lifetime
- Remove wildcard-friendly defaults in public API middleware
- Centralize new secret fields in config settings

### Implementation Status
- [x] `backend/ai_receptionist/utils/encryption.py`
  - Removed hardcoded fallback secret
  - Added strict Fernet key validation for `ENCRYPTION_KEY`
  - Added fail-fast if neither `ENCRYPTION_KEY` nor `ADMIN_PRIVATE_KEY` is configured
- [x] `backend/ai_receptionist/app/api/auth.py`
  - Added `JWT_SECRET_KEY` as primary signing key
  - Added fallback warning path to `ADMIN_PRIVATE_KEY`
  - Reduced token TTL from 24h to 1h
  - Added `nbf` claim
- [x] `frontend/portfolio/main.py`
  - Changed default `ALLOWED_ORIGINS` from `*` to explicit production origins
  - Removed `TrustedHostMiddleware` wildcard bypass in non-production mode
- [x] `backend/ai_receptionist/config/settings.py`
  - Added `ENCRYPTION_KEY` and `JWT_SECRET_KEY` fields

### Codex Follow-up Tasks (Sprint 1 complete-out)
- [ ] Update `.env.example` files with `ENCRYPTION_KEY` and `JWT_SECRET_KEY`
- [ ] Add startup validation warning/error policy for missing production secrets
- [ ] Add tests for `_jwt_key()` precedence and TTL/claims shape

### Acceptance Criteria
- App refuses insecure encryption config at runtime
- JWT tokens expire in <= 1 hour
- CORS default is no longer wildcard
- Trusted host middleware never falls back to `*`

---

## Sprint 2 — Rate Limiting + Container Hardening

### Implementation Status
- [x] `frontend/portfolio/main.py`
   - Changed limiter storage default from `memory://` to Redis URI
   - Added password-aware default URI behavior via `REDIS_PASSWORD`
   - Preserved `RATE_LIMIT_STORAGE` env override
- [x] `backend/docker-compose.prod.yml`
   - Added Redis auth (`--requirepass`) and append-only persistence (`--appendonly yes`)
   - Added authenticated Redis healthcheck
- [x] `backend/docker-compose.dev.yml`
   - Added Redis auth with local default password
   - Restricted host exposure to `127.0.0.1:6379`
   - Added Redis volume + healthcheck
- [x] `backend/Dockerfile` and `frontend/portfolio/Dockerfile`
   - Added non-root runtime users
   - Added image-level healthchecks
- [x] `.env.example` updates
   - Added Redis password + secure limiter URI examples

### Codex Tasks
1. `frontend/portfolio/main.py`
   - Change limiter storage default from `memory://` to Redis URI
   - Support env override via `RATE_LIMIT_STORAGE`
2. `backend/docker-compose.prod.yml` and `backend/docker-compose.dev.yml`
   - Ensure Redis is configured with auth (dev/prod-specific env)
   - Avoid accidental host exposure in prod
3. `backend/Dockerfile` and `frontend/portfolio/Dockerfile`
   - Add non-root runtime user
   - Add `HEALTHCHECK` instructions

### Acceptance Criteria
- Rate-limit counters shared across workers
- Containers run as non-root users
- Redis setup does not expose unauthenticated prod access

---

## Sprint 3 — Encryption Salt Rotation + Migration

### Implementation Status
- [x] `backend/ai_receptionist/utils/encryption.py`
   - Added `ENCRYPTION_SALT` support with base64 decoding/validation
   - Added legacy-salt fallback decryption path for migration safety
   - Added helper `generate_encryption_salt()`
   - Added explicit-salt encrypt/decrypt helpers for migration utility
- [x] `backend/ai_receptionist/config/settings.py`
   - Added `ENCRYPTION_SALT` settings field
- [x] `backend/ai_receptionist/app/main.py`
   - Added startup critical warning when legacy/default salt is detected
- [x] `backend/scripts/migrate_encrypt_tokens.py`
   - Added dry-run migration script with strict non-zero exit on decrypt failures
   - Supports `--old-salt` and `--new-salt`

### Runbook (Codex/Ops)
1. Generate and set new salt (`ENCRYPTION_SALT`) in target environment.
2. Execute dry run: `python scripts/migrate_encrypt_tokens.py --dry-run`.
3. Execute live migration: `python scripts/migrate_encrypt_tokens.py`.
4. Restart app containers and verify calendar integration token usage.
5. Monitor logs for any `legacy salt fallback` warnings; warnings should drop to zero.

### Codex Tasks
1. Extend `encryption.py` to support env-managed `ENCRYPTION_SALT`
2. Add migration script:
   - Read existing encrypted OAuth tokens
   - Decrypt with legacy salt path
   - Re-encrypt with new salt path
   - Support dry-run mode
3. Add settings field for `ENCRYPTION_SALT`

### Acceptance Criteria
- Existing tokens remain decryptable after migration
- New writes use rotated salt configuration
- Migration script is repeatable and idempotent-safe

---

## Sprint 4 — Auth Lifecycle + Operations Verification

### Implementation Status
- [x] `backend/ai_receptionist/app/api/auth.py`
   - Added `jti` claim to issued JWTs
   - Added Redis-backed revoked-token (`jti`) checks
   - Added `POST /api/auth/logout` to revoke active token `jti`
   - Added `POST /api/auth/refresh` to issue bounded renewed token
   - Added failed-login throttling via Redis (`login_fails:{username}`)
- [x] `backend/ai_receptionist/config/settings.py`
   - Added `redis_password` support in settings and URL generation path
- [x] `docs/infra/server-hardening.md`
   - Added executable production verification checklist

### Codex Tasks
1. `backend/ai_receptionist/app/api/auth.py`
   - Add refresh token flow or bounded token refresh endpoint
   - Add `jti` and revocation strategy (Redis-backed)
2. Add brute-force throttling for failed login attempts
3. Update ops docs with executable verification checklist
4. Reconcile stale completion statements in implementation docs

### Acceptance Criteria
- Logout/refresh/revoke lifecycle is enforceable
- Brute-force attempts trigger lockout/rate controls
- Security docs match runtime reality

---

## Validation Notes (Current Run)
- Python syntax checks passed for modified backend files
- Python syntax check passed for `frontend/portfolio/main.py`
- Auth lifecycle integration tests passed: `py -m pytest ai_receptionist/tests/test_auth_lifecycle.py -q` (3 passed)
   - `refresh` issues renewed token with new `jti`
   - `logout` revokes token and blocks reuse on `/api/auth/me`
   - failed-login lockout returns `429` on 5th invalid attempt
- Production deployment and verification completed on host (`http://localhost:8002`):
   - Backend app service rebuilt/recreated with Sprint 4 auth code
   - `REDIS_URL=redis://redis:6379/0` configured for app container to enable Redis-backed auth state
   - `/api/auth/refresh` now present in OpenAPI and returns `200` with renewed token
   - `/api/auth/logout` now revokes bearer token (`/api/auth/me` returns `401` for logged-out token)
   - Failed-login lockout enforces `429` on 5th bad attempt and blocks immediate correct-login retry
- Existing unrelated test collection error still present in `backend/tests/test_voice_webhook.py` (`ModuleNotFoundError: src`)

---

## Deployment Guardrails
- Do not deploy Sprint 1 to production until env secrets are confirmed on host
- Rotate exposed Stripe secrets outside code changes
- Roll out with one host/container first, then full fleet
