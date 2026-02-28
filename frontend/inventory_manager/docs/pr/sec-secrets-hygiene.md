# PR: Secrets Hygiene

Title: sec: secrets hygiene (.gitignore, pre-commit, CI gitleaks)

What changed:
- Ensure secrets are ignored in VCS: `.env`, `service_account.json`, `*-credentials.json`, `*.json.secret`, ngrok tokens
- Pre-commit hook to block committing `.env` and key-like JSON (`.pre-commit-config.yaml`)
- CI: gitleaks secrets scan with SARIF upload (security.yml)
- Incident response guide added: `docs/SECURITY_INCIDENT.md`

Why:
- Reduce risk of credential exposure for class demos and development

Verification:
- `git add .env` should be blocked by pre-commit
- CI should run Gitleaks and upload a SARIF artifact on PRs

Follow-ups:
- Rotate any previously exposed tokens and purge history per `docs/SECURITY_INCIDENT.md`
