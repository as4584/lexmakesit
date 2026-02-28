# Backend Documentation

> Documentation for the AI Receptionist FastAPI backend service.

---

## Documents

| Document | Purpose |
|----------|---------|
| [source-of-truth.md](source-of-truth.md) | **START HERE** — Critical config, ports, endpoints, DO NOT CHANGE items |
| [architecture.md](architecture.md) | System architecture, call flow, tech stack, file structure |
| [cost-analysis.md](cost-analysis.md) | Cost breakdown, optimization options, pricing models |
| [performance.md](performance.md) | Speed optimization, silence bug fix, performance changelog |
| [evaluation-system.md](evaluation-system.md) | Offline testing framework for conversation flows |
| [technical-debt.md](technical-debt.md) | Tech debt audit, action plan, priority matrix |
| [calendar-integration.md](calendar-integration.md) | Google Calendar integration plan & implementation guide |

---

## Key Facts

- **Framework**: FastAPI (Python 3.10+)
- **AI Model**: OpenAI GPT-4o Realtime API
- **Voice**: Twilio Media Streams → OpenAI Realtime → caller
- **Server**: `174.138.67.169` (`lex@174.138.67.169`)
- **Container**: `ai_receptionist_app` on port 8010
- **Domain**: `receptionist.lexmakesit.com`
- **GitHub**: `as4584/cookie-cutter-receptionist`

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-02-28 | Consolidated from scattered docs across backend/ and backend/docs/ | Antigravity |
