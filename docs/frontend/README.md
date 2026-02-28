# Frontend Documentation

> Documentation for all frontend applications: Dashboard, Portfolio, and Inventory Manager.

---

## Applications

| App | Path | Tech Stack | Domain | Port |
|-----|------|------------|--------|------|
| **Portfolio** | `frontend/portfolio/` | FastAPI + Jinja2 | `lexmakesit.com` | 8001 → 8000 |
| **AI Receptionist Dashboard** | `frontend/ai_receptionist/` | React/Next.js | `dashboard.lexmakesit.com` | — |
| **Inventory Manager** | `frontend/inventory_manager/` | Flask + React/Jinja2 | — | — |

---

## Portfolio Site

### Architecture
- **Backend**: FastAPI with Jinja2 templates
- **Static**: `static/css/`, `static/js/`, `static/images/`
- **Container**: `portfolio-web-1` via Docker Compose
- **Server**: `lex@104.236.100.245`
- **Path on server**: `~/antigravity_bundle/apps/portfolio`

### Deployment
See [/docs/infra/deployment.md](/docs/infra/deployment.md) and the `/deploy-portfolio` workflow.

---

## AI Receptionist Dashboard

### Architecture
- React/Next.js frontend for managing AI receptionist settings
- Connects to backend API at `receptionist.lexmakesit.com`
- Manages: business plans, phone numbers, onboarding wizard

### Key Components
- Onboarding wizard (multi-step)
- Dashboard page with receptionist status
- Plan selection and management
- Google Calendar integration (planned)

---

## Inventory Manager

### Architecture
- Flask backend + React/Jinja2 frontend
- Lightspeed API integration for POS data
- TDD workflow with security checklist

### Key Docs (from source)
- Lightspeed API overview
- Security checklist
- TDD workflow
- Versioning guide

---

## Design System

### UI Philosophy
- **Frutiger Aero** aesthetic (glassmorphism, vibrant gradients, dynamic animations)
- Modern typography (Inter, Roboto, Outfit)
- Dark mode support
- Responsive layouts

### Templates
See `frontend/docs/ui-design-templates.md` for pipeline templates.

---

## CI/CD
Frontend services use path-filtered GitHub Actions triggers. See [/docs/infra/ci-cd.md](/docs/infra/ci-cd.md).

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-02-28 | Consolidated from frontend/docs/, frontend/ai_receptionist/, frontend/portfolio/docs/ | Antigravity |
