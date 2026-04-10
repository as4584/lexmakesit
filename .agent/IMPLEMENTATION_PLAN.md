# 🚀 AI Receptionist Platform - Implementation Plan
**Created**: 2026-01-19
**Owner**: thegamermasterninja@gmail.com
**Status**: In Progress ✅

---

## 🔐 SECURITY HARDENING UPDATE (2026-03-06)

### Sprint 1 Started — Implemented in Code ✅
- [x] Removed hardcoded encryption fallback secret in `backend/ai_receptionist/utils/encryption.py`
- [x] Added strict `ENCRYPTION_KEY` validation for Fernet format
- [x] Added fail-fast behavior when no encryption secret is configured
- [x] Reduced JWT token TTL from 24h to 1h in `backend/ai_receptionist/app/api/auth.py`
- [x] Added `JWT_SECRET_KEY` support with controlled fallback to `ADMIN_PRIVATE_KEY`
- [x] Added `nbf` claim to issued JWTs for safer validation windows
- [x] Replaced wildcard CORS default with explicit production domains in `frontend/portfolio/main.py`
- [x] Removed TrustedHost wildcard bypass in non-production mode
- [x] Added `ENCRYPTION_KEY` and `JWT_SECRET_KEY` fields to centralized settings in `backend/ai_receptionist/config/settings.py`

### Verification Pending
- [ ] Run backend auth tests (`pytest backend/tests -k auth`)
- [ ] Run portfolio API smoke tests for CORS + host middleware behavior
- [ ] Confirm environment variables are set on production hosts before rollout

### Sprint 2 Started — Implemented in Code ✅
- [x] Moved portfolio rate limiting storage default to Redis with env override in `frontend/portfolio/main.py`
- [x] Added Redis-password-aware limiter default URI generation
- [x] Added non-root runtime users and healthchecks to `backend/Dockerfile` and `frontend/portfolio/Dockerfile`
- [x] Hardened Redis in `backend/docker-compose.prod.yml` with auth + AOF persistence + authenticated healthcheck
- [x] Hardened Redis in `backend/docker-compose.dev.yml` with auth, localhost-only bind, volume, and healthcheck
- [x] Updated env templates with `REDIS_PASSWORD` and secure `RATE_LIMIT_STORAGE` examples

### Sprint 2 Verification Pending
- [ ] Validate compose config with environment substitution (`docker compose config`)
- [ ] Launch stack and verify Redis auth-required behavior
- [ ] Confirm rate limit behavior across multiple workers

### Sprint 3 Started — Implemented in Code ✅
- [x] Added env-managed encryption salt support in `backend/ai_receptionist/utils/encryption.py`
- [x] Added legacy-salt fallback decryption path with migration warning logging
- [x] Added `ENCRYPTION_SALT` field in centralized settings (`backend/ai_receptionist/config/settings.py`)
- [x] Added startup critical warning in `backend/ai_receptionist/app/main.py` when legacy/default salt remains configured
- [x] Created migration utility `backend/scripts/migrate_encrypt_tokens.py` with `--dry-run`, old/new salt support, and non-zero exit on failures
- [x] Updated backend env template with `ENCRYPTION_SALT`

### Sprint 3 Verification Pending
- [ ] Run `python scripts/migrate_encrypt_tokens.py --dry-run` in backend environment
- [ ] Rotate `ENCRYPTION_SALT` in deployment env and run live migration
- [ ] Confirm calendar token decrypt/refresh works after migration

### Sprint 4 Started — Implemented in Code ✅
- [x] Added JWT `jti` claim generation in `backend/ai_receptionist/app/api/auth.py`
- [x] Added Redis-backed token revocation checks in auth token decode path
- [x] Added `POST /api/auth/logout` revocation behavior for bearer token `jti`
- [x] Added `POST /api/auth/refresh` endpoint for bounded token renewal
- [x] Added failed-login throttling (5 attempts / 15 minutes) with Redis counters
- [x] Added Redis password support in settings-derived URL logic (`backend/ai_receptionist/config/settings.py`)
- [x] Added server hardening verification checklist to `docs/infra/server-hardening.md`

### Sprint 4 Verification Pending
- [x] Validate `refresh` and `logout` routes with valid/invalid bearer tokens (local integration test)
- [x] Validate revocation blocks reused logged-out tokens (local integration test)
- [x] Validate brute-force lockout returns `429` after 5 failed attempts (local integration test)
- [x] Verify Redis-backed auth state on production environment
- [x] Validate the same lifecycle checks against deployed production/staging API

### Sprint 4 Production Verification (2026-03-06)
- [x] Probed live auth OpenAPI on server (`http://localhost:8002/openapi.json`)
- [x] Confirmed initial production route mismatch: `/api/auth/refresh` not present on deployed backend
- [x] Confirmed initial logout did not revoke bearer token on deployed backend (`/api/auth/me` remained `200`)
- [x] Deployed Sprint 4 auth changes to production app service and set `REDIS_URL=redis://redis:6379/0`
- [x] Re-validated production auth lifecycle:
   - `POST /api/auth/refresh` returns `200` with a new access token
   - `POST /api/auth/logout` revokes current token (`/api/auth/me` returns `401` for logged-out token)
   - failed login lockout triggers `429` on 5th bad attempt and blocks immediate correct login

---

## ✅ COMPLETED TODAY (2026-01-19)

### Workstream 1: Mobile UI ✅
- Added responsive CSS for 768px and 480px breakpoints
- Hamburger menu for mobile navigation
- Pricing cards stack vertically on mobile
- Touch-friendly buttons (min 48px tap targets)

### Workstream 2: Real-time Features ✅
- Calendar now shows actual current date (January 19, 2026)
- Real-time clock updates every second
- Calendar properly calculates days in month and first day of week
- Live transcript shows properly formatted conversation

### Workstream 5: Stripe Payments ✅
- Added Stripe credentials to server `.env`
- Created `/api/stripe/create-checkout-session` endpoint
- Created `/api/stripe/webhook` endpoint for payment processing
- Pricing buttons now trigger Stripe checkout
- Welcome email sends after successful purchase

### Workstream 6: Pricing CTAs ✅
- "Get Started" button → Stripe checkout (Starter tier)
- "Start Free Pilot" button → Stripe checkout (Professional tier)
- "Contact Sales" buttons → Home contact form

---
1. **Mobile-friendly UI** - Responsive design improvements
2. **Real-time Dashboard Features** - Live calendar, clock, and transcript
3. **Phone Number Integration** - Twilio dropdown + linked number display
4. **Improved Onboarding Flow** - Better business profile setup
5. **Stripe Payment Integration** - Purchase flow + email access
6. **Pricing Page CTA Links** - Connect to dashboard/signup

---

## 🔧 WORKSTREAM 1: Mobile-Friendly UI (Frontend)

### Goal
Make the AI Receptionist page fully responsive and mobile-optimized following Frutiger Aero design principles.

### Tasks
- [ ] Add proper viewport meta tags
- [ ] Implement CSS media queries for mobile breakpoints (320px, 480px, 768px)
- [ ] Stack pricing cards vertically on mobile
- [ ] Responsive navigation (hamburger menu)
- [ ] Touch-friendly button sizes (min 44px tap targets)
- [ ] Test on actual mobile devices

### Files to Modify
- `frontend/portfolio/templates/ai-receptionist.html`
- `frontend/portfolio/static/css/global.css`
- `frontend/portfolio/static/css/components.css`

---

## 🔧 WORKSTREAM 2: Real-Time Dashboard Features (Frontend + Backend)

### Goal
Make the dashboard calendar, clock, and live transcript accurate and real-time.

### Tasks

#### 2a. Schedule/Booking Calendar
- [ ] Display today's date correctly (JavaScript `new Date()`)
- [ ] Highlight current day
- [ ] Show current month/year dynamically
- [ ] Add real-time clock display

#### 2b. Live Transcript
- [ ] Connect to WebSocket for real call data
- [ ] Display actual transcription from Twilio/OpenAI
- [ ] Color-code caller (blue) vs AI (green) properly

### Files to Modify
- Dashboard frontend (Next.js or equivalent)
- Backend WebSocket handler
- `ai_receptionist/` modules

---

## 🔧 WORKSTREAM 3: Phone Number Integration (Backend + Frontend)

### Goal
Link thegamermasterninja@gmail.com to a Twilio phone number and display it in the dashboard.

### Tasks

#### 3a. Twilio Phone Number Dropdown
- [ ] Create API endpoint to fetch available Twilio numbers
- [ ] Build dropdown component in onboarding UI
- [ ] Allow selection and assignment of number to user

#### 3b. Phone Number Display
- [ ] Show assigned phone number in dashboard header
- [ ] Add "Copy Number" functionality
- [ ] Display phone status (active/inactive)

### Backend Endpoints Needed
```python
GET  /api/twilio/available-numbers  # List purchasable numbers
GET  /api/twilio/my-numbers         # User's assigned numbers
POST /api/twilio/assign-number      # Assign number to user
```

### Twilio API Requirements
- Twilio Account SID
- Twilio Auth Token
- Access to Twilio Phone Numbers API

---

## 🔧 WORKSTREAM 4: Improved Onboarding Flow (Frontend + Backend)

### Goal
Create a comprehensive onboarding wizard that helps the AI receptionist better represent the business owner.

### Onboarding Steps
1. **Business Profile**
   - Business name
   - Industry/vertical
   - Business hours
   - Location/timezone

2. **Phone Number Selection**
   - Dropdown of available Twilio numbers
   - Area code preference
   - Number porting option

3. **AI Persona Setup**
   - Greeting style (formal/casual/friendly)
   - Key FAQs to answer
   - Services offered
   - Custom responses

4. **Calendar Integration**
   - Connect Google Calendar
   - Set booking rules
   - Define appointment types

5. **Test Call**
   - Make a test call to verify setup
   - Review transcript
   - Approve or adjust

### Files to Create
- `frontend/dashboard/components/OnboardingWizard.tsx`
- `backend/ai_receptionist/onboarding/` module

---

## 🔧 WORKSTREAM 5: Stripe Payment Integration

### Goal
Allow customers to purchase an AI receptionist subscription and receive dashboard access.

### Purchase Flow
1. User clicks pricing tier button ("Get Started")
2. Redirect to Stripe Checkout
3. On success, create user account
4. Send email with login link
5. User accesses dashboard

### Stripe Information Needed from You
To implement Stripe, I need:
- [ ] **Stripe Publishable Key** (pk_live_xxx or pk_test_xxx)
- [ ] **Stripe Secret Key** (sk_live_xxx or sk_test_xxx)
- [ ] **Stripe Webhook Signing Secret** (whsec_xxx)
- [ ] **Product IDs** for each pricing tier (or I can create them)
- [ ] **Price IDs** for each tier's monthly/annual pricing

### Backend Endpoints Needed
```python
POST /api/stripe/create-checkout-session
POST /api/stripe/webhook  # Handle payment success
GET  /api/stripe/subscription-status
```

### Files to Create/Modify
- `backend/ai_receptionist/payments/` module
- `frontend/portfolio/templates/checkout.html`
- `frontend/dashboard/pages/login.tsx` (add signup)

---

## 🔧 WORKSTREAM 6: Pricing Page CTAs (Frontend)

### Goal
Connect the pricing tier buttons to the dashboard/signup flow.

### Tasks
- [ ] "Get Started" → Stripe Checkout (Starter tier)
- [ ] "Start Free Pilot" → Signup/Login + Pilot flag
- [ ] "Contact Sales" → Contact form or email link
- [ ] Add proper tracking (UTM params)

---

## 📊 Priority Matrix

| Workstream | Priority | Effort | Dependencies |
|------------|----------|--------|--------------|
| WS1: Mobile UI | High | Medium | None |
| WS2: Real-time Features | High | High | Backend APIs |
| WS3: Phone Integration | High | Medium | Twilio credentials |
| WS4: Onboarding | Medium | High | WS3 complete |
| WS5: Stripe Integration | High | Medium | Stripe credentials |
| WS6: Pricing CTAs | Medium | Low | WS5 complete |

---

## 📝 Immediate Next Steps

1. **You Provide**: Stripe API keys (test mode is fine to start)
2. **You Provide**: Confirm Twilio credentials are already configured
3. **I Start**: Mobile UI improvements (WS1)
4. **I Start**: Real-time calendar/clock fix (WS2a)

---

## 🔐 Credentials Checklist

### Already Have
- [x] SSH access to droplet
- [x] GitHub repository access
- [ ] Twilio Account SID & Auth Token (confirm)
- [ ] Stripe API keys (needed from you)

### For Stripe - What I Need
Please provide (in a secure way):
1. `STRIPE_PUBLISHABLE_KEY` - Public key for frontend
2. `STRIPE_SECRET_KEY` - Secret key for backend
3. `STRIPE_WEBHOOK_SECRET` - For verifying webhook signatures

You can create these at: https://dashboard.stripe.com/apikeys

---

## 🏗️ TDD Workflow Upgrade

I'm upgrading the workflow file to include all testing commands.
