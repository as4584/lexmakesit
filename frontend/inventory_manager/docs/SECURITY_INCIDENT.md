# Security Incident Response Guide

This document outlines the steps to take if secrets are accidentally committed or a security incident is suspected.

## 1) Triage
- Identify the leaked secret(s): API keys, service accounts, ngrok tokens, etc.
- Determine exposure window and impacted systems.
- Create an internal incident ticket.

## 2) Containment
- Immediately invalidate/rotate the affected credentials.
- Remove secrets from the repository history:
  - Use `git filter-repo` or GitHub’s “Remove sensitive data” guide.
  - Force push to remove the history (coordinate with the team).
- Ensure `.gitignore` blocks committed file types (e.g., .env, service_account.json).

## 3) Eradication
- Add pre-commit hooks to prevent future commits containing sensitive files.
- Add CI secrets scanning (Gitleaks) and monitor alerts.
- Update documentation to reinforce secret hygiene.

## 4) Recovery
- Deploy rotated credentials and verify systems function normally.
- Add required status checks to CI/CD for security jobs.
- Review access logs for anomalies.

## 5) Lessons Learned
- Document root cause and prevention measures.
- Provide a short training note for contributors.

## References
- Gitleaks: https://github.com/gitleaks/gitleaks
- GitHub Secret Scanning: https://docs.github.com/en/code-security
- Git Filter Repo: https://github.com/newren/git-filter-repo
