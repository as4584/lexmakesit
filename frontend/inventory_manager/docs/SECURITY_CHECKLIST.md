# OWASP Top 10 Security Checklist - Level 1

## Overview

This checklist is based on the **[OWASP Top 10](https://owasp.org/www-project-top-ten/)** web application security risks. Use this for security reviews of pull requests and releases.

**Review Level**: **Level 1** (Essential/Critical only)

---

## 🛡️ Pre-Deployment Security Checklist

### A01:2021 – Broken Access Control

- [ ] **Authentication Required**
  - All sensitive endpoints require authentication
  - No admin functions accessible without proper authorization
  - Session management is secure (timeouts, secure cookies)

- [ ] **Authorization Checks**
  - Users can only access their own data
  - Role-based access control (RBAC) implemented where needed
  - Direct object references are validated (no IDOR vulnerabilities)

- [ ] **CORS Configuration**
  - CORS headers properly configured (not `*` in production)
  - Only trusted origins allowed

**Status**: 🟡 Partial  
**Notes**: Currently no authentication (internal tool only). Add before external deployment.

---

### A02:2021 – Cryptographic Failures

- [ ] **Data Encryption**
  - Sensitive data encrypted at rest (Google Sheets has built-in encryption)
  - HTTPS/TLS enforced for all external communication
  - No plain-text credentials in configuration files

- [ ] **Secrets Management**
  - API tokens stored in environment variables (not in code)
  - `.env` file in `.gitignore`
  - No secrets committed to Git history

- [ ] **Password Storage** (N/A - no user passwords)
  - If implemented: Use bcrypt/Argon2 for password hashing
  - Minimum 12-character passwords required
  - No password stored in plain text

**Status**: ✅ Compliant  
**Notes**: All secrets in environment variables, `.env.example` provided.

---

### A03:2021 – Injection

- [ ] **SQL Injection Prevention** (N/A - no SQL database)
  - If using SQL: Parameterized queries/ORM used exclusively
  - No string concatenation for queries

- [ ] **Command Injection Prevention**
  - No `os.system()` or `subprocess.call()` with user input
  - Shell commands sanitized if unavoidable
  - Use `shlex.quote()` for escaping

- [ ] **NoSQL Injection Prevention** (N/A)
  - If using MongoDB/NoSQL: Input validation and sanitization

- [ ] **LDAP/XPath Injection** (N/A)
  - Input properly escaped if LDAP/XPath queries used

**Status**: ✅ Compliant  
**Notes**: No direct database queries. Pandas and gspread used safely.

---

### A04:2021 – Insecure Design

- [ ] **Threat Modeling**
  - Security considered in design phase
  - Attack surface minimized
  - Defense in depth applied

- [ ] **Rate Limiting**
  - API endpoints have rate limiting (Lightspeed API: 0.5s delay)
  - Protection against brute force attacks
  - DDoS mitigation considered

- [ ] **Input Validation**
  - All user input validated (whitelist approach)
  - File uploads restricted by type and size
  - CSV uploads validated before processing

**Status**: 🟡 Partial  
**Notes**: Rate limiting for external API. Add rate limiting for Flask endpoints.

---

### A05:2021 – Security Misconfiguration

- [ ] **Default Credentials**
  - No default passwords or API keys
  - All credentials must be explicitly set

- [ ] **Debug Mode Disabled**
  - Flask `DEBUG=False` in production
  - No verbose error messages exposing internals
  - Stack traces not shown to users

- [ ] **Unnecessary Features Disabled**
  - No unused dependencies installed
  - Minimal attack surface
  - Remove commented-out code

- [ ] **Security Headers**
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Strict-Transport-Security` (HSTS) if HTTPS
  - `Content-Security-Policy` configured

**Status**: 🟡 Partial  
**Notes**: Add security headers to Flask app. Ensure DEBUG=False in production.

---

### A06:2021 – Vulnerable and Outdated Components

- [ ] **Dependency Scanning**
  - `pip-audit` run regularly (weekly via Dependabot)
  - `safety check` passes with no critical vulnerabilities
  - All dependencies up to date

- [ ] **Dependency Pinning**
  - `requirements.txt` with pinned versions
  - Automated updates via Dependabot
  - Test before applying updates

- [ ] **EOL Software Avoided**
  - Python 3.11+ (supported until 2027)
  - No deprecated libraries in use

**Status**: ✅ Compliant  
**Notes**: Dependabot enabled, pip-audit in CI, Safety checks automated.

---

### A07:2021 – Identification and Authentication Failures

- [ ] **Multi-Factor Authentication** (N/A - internal tool)
  - If public-facing: Require MFA for admin accounts

- [ ] **Session Management** (N/A - no sessions yet)
  - If implemented: Secure session tokens (httpOnly, secure flags)
  - Session timeout after inactivity
  - Logout functionality destroys sessions

- [ ] **Credential Recovery** (N/A)
  - If implemented: Secure password reset flow
  - No security questions (use email/SMS verification)

**Status**: 🟢 N/A  
**Notes**: No authentication currently. Implement before external access.

---

### A08:2021 – Software and Data Integrity Failures

- [ ] **Code Integrity**
  - Dependencies installed from trusted sources (PyPI)
  - `pip` uses HTTPS for package downloads
  - Consider using `pip-audit` for supply chain attacks

- [ ] **CI/CD Pipeline Security**
  - GitHub Actions secrets properly configured
  - No secrets in workflow logs
  - Workflow permissions minimized (principle of least privilege)

- [ ] **Deserialization**
  - No `pickle` or `yaml.load()` on untrusted data
  - Use `json.loads()` for safe parsing
  - Validate data structure after deserialization

**Status**: ✅ Compliant  
**Notes**: JSON used for data. No unsafe deserialization.

---

### A09:2021 – Security Logging and Monitoring Failures

- [ ] **Logging Implemented**
  - Authentication attempts logged (when implemented)
  - Errors and exceptions logged
  - Security events logged (failed validation, rate limiting)

- [ ] **No Sensitive Data in Logs**
  - No passwords, tokens, or PII in logs
  - Logs sanitized before storage
  - API tokens redacted in error messages

- [ ] **Log Monitoring**
  - Logs aggregated and monitored (future: use CloudWatch, Datadog, etc.)
  - Alerts for suspicious activity
  - Log retention policy defined

- [ ] **Audit Trail**
  - SalesLog worksheet tracks all sales operations
  - Inventory changes logged with timestamps
  - User actions traceable (when multi-user implemented)

**Status**: 🟡 Partial  
**Notes**: Basic logging exists. Add structured logging and monitoring.

---

### A10:2021 – Server-Side Request Forgery (SSRF)

- [ ] **External Request Validation**
  - Whitelist allowed external domains (Lightspeed API, Google Sheets API)
  - No user-controlled URLs in API requests
  - DNS rebinding protection

- [ ] **Internal Network Isolation**
  - Application cannot access internal network from user input
  - Metadata endpoints blocked (e.g., AWS metadata at 169.254.169.254)

**Status**: ✅ Compliant  
**Notes**: Only predefined API endpoints contacted. No user-controlled URLs.

---

## 🔍 Code Review Security Checklist

Use this when reviewing PRs:

### Input Validation
- [ ] All user input validated (type, length, format)
- [ ] CSV uploads checked for malicious content
- [ ] File size limits enforced
- [ ] Allowlist validation (not just blocklist)

### Output Encoding
- [ ] HTML output properly escaped (Jinja2 auto-escapes)
- [ ] JSON responses use `jsonify()` (prevents injection)
- [ ] CSV exports sanitize formula injection (`=`, `+`, `-`, `@`)

### Error Handling
- [ ] Try-except blocks don't expose sensitive info
- [ ] Generic error messages to users
- [ ] Detailed errors logged server-side only
- [ ] No stack traces in production responses

### API Security
- [ ] Lightspeed API tokens not logged
- [ ] Google service account JSON not in version control
- [ ] Rate limiting respected (0.5s delay between requests)
- [ ] Retry logic has max attempts (prevent infinite loops)

### Data Validation
- [ ] CSV parsing validates column names
- [ ] Numeric fields validated (price, quantity > 0)
- [ ] Date formats validated before processing
- [ ] Barcode/SKU formats validated

---

## 🚨 Security Incident Response

If a security issue is found:

1. **Do NOT** commit the fix to a public branch immediately
2. Follow `SECURITY.md` responsible disclosure process
3. Create a **private** security advisory on GitHub
4. Coordinate patch release with maintainers
5. Notify users after patch is available

---

## 🛠️ Security Tools Integration

### Automated Scans (CI/CD)

✅ **Bandit** - Python security linter
```bash
bandit -r services/ jobs/ app.py
```

✅ **Safety** - Dependency vulnerability scanner
```bash
safety check
```

✅ **pip-audit** - PyPI package auditor
```bash
pip-audit
```

✅ **CodeQL** - Static analysis (weekly GitHub scan)

### Manual Security Testing

🔧 **OWASP ZAP** - Web app security scanner (run before major releases)
```bash
docker run -t owasp/zap2docker-stable zap-baseline.py -t http://localhost:8000
```

🔧 **Grype** - Container vulnerability scanner (if Docker deployed)
```bash
grype dir:.
```

---

## 📋 Pre-Release Security Sign-Off

Before tagging a release:

- [ ] All CI security checks pass (Bandit, Safety, pip-audit)
- [ ] CodeQL scan shows no high/critical issues
- [ ] No known CVEs in dependencies
- [ ] This checklist reviewed and compliant
- [ ] Security-sensitive changes reviewed by @HEAD_DEVELOPER
- [ ] Changelog includes security fixes (if any)
- [ ] `.env.example` up to date (no secrets exposed)

**Release Manager**: _____________  
**Date**: _____________  
**Version**: _____________

---

## 📚 Resources

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **OWASP Cheat Sheets**: https://cheatsheetseries.owasp.org/
- **Python Security**: https://bandit.readthedocs.io/
- **Flask Security**: https://flask.palletsprojects.com/en/3.0.x/security/

---

## 🔄 Review Schedule

- **Per PR**: Quick checklist review (5-10 min)
- **Per Release**: Full checklist review (30 min)
- **Quarterly**: Deep security audit (2-4 hours)
- **Annual**: External penetration testing (if budget allows)

---

## ✅ Current Security Posture

| Area | Status | Notes |
|------|--------|-------|
| Input Validation | 🟢 Good | CSV validated, Pandas sanitizes data |
| Output Encoding | 🟢 Good | Jinja2 auto-escapes, jsonify used |
| Secrets Management | 🟢 Good | Environment variables, no commits |
| Dependency Scanning | 🟢 Good | Automated via CI, Dependabot enabled |
| Access Control | 🟡 Pending | No auth yet (internal tool only) |
| Logging | 🟡 Partial | Basic logging, needs structured logs |
| Security Headers | 🔴 Missing | Add Flask-Talisman for headers |
| Rate Limiting | 🟡 Partial | External API only, add for Flask |

**Legend**:
- 🟢 Good - Meets requirements
- 🟡 Partial - Some gaps, acceptable for internal use
- 🔴 Missing - Must fix before external deployment

---

**Version**: 1.0  
**Last Updated**: 2025-10-10  
**Next Review**: 2026-01-10 (quarterly)
