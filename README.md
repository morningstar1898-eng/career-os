# Career OS

**A human-in-the-loop AI career operating system for data and AI job seekers.**

Career OS helps find job opportunities, score job fit, draft application materials, track pipeline status, identify missing skills, generate teaching moments and interview practice, and produce daily career briefings. It began as a private single-user system and now also contains a multi-user SaaS foundation (`/v1` API) with accounts, a 3-day no-card trial, plans/entitlements, and a Gmail feedback-loop scaffold.

**It does not auto-submit job applications.** Agents find jobs and draft materials; the user reviews everything and submits every application themselves. The pipeline enforces this in code: automation can only create `Found`, `Saved`, `Drafted`, or `Ready to Apply` records — only an explicit user action (or a confirmed application email) moves a job to `Applied`/`Confirmation Received`, and every change is recorded in event history.

> Branding note: "CareerOS" is the internal name; the user-facing name is configurable via `PUBLIC_APP_NAME` / `NEXT_PUBLIC_APP_NAME` until the external SaaS brand is chosen.

---

## What it does each weekday morning

| Agent | Action |
|-------|--------|
| Skills Scout | Scans job boards + company careers pages, extracts skill trends, logs verified postings as **Found** |
| Materials Drafter | Drafts tailored resume bullets + cover letters for the top roles (for the owner's review) |
| Tutor | Writes a deep daily lesson targeting the biggest skill gap |
| Data Analyst | Proposes a portfolio project concept from a real public dataset |
| Interview Coach | Generates 10 practice questions with model answers |
| Follow-up Tracker | Flags manually-applied jobs that have gone quiet for 7+ days |
| LinkedIn Optimizer (Mondays) | Audits profile keywords against the week's postings |
| Orchestrator | Compiles everything into a Notion page + emailed briefing |

The owner's daily input: read the briefing, review drafts, and decide what to actually apply to.

## What it does NOT do

- ❌ Submit job applications
- ❌ Mark jobs as "Applied" automatically
- ❌ Send messages to recruiters
- ❌ Change your LinkedIn profile
- ❌ Log jobs without a real posting URL from search results

---

## Architecture

```
GitHub Actions (weekday cron)                Vercel
┌─────────────────────────┐          ┌──────────────────┐
│ CrewAI crew (main.py)   │          │ Next.js 16       │
│ 6-8 agents, Claude API  │          │ dashboard        │
│  → Notion briefing      │          │ (password gate + │
│  → Google Sheets log    │          │  bearer token)   │
│  → Azure Blob materials │          └───────┬──────────┘
└──────────┬──────────────┘                  │ REST + WS (Bearer token)
           │ POST /ingest/* (token + secret) │
┌──────────▼──────────────────────────────────▼─────────┐
│ FastAPI backend — Docker container on Azure App Service│
│ SQLite (CAREER_OS_DB → persistent mount)               │
│ briefings · pipeline Kanban · interview · analytics    │
└────────────────────────────────────────────────────────┘
```

More detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · Security model: [docs/SECURITY.md](docs/SECURITY.md) · Demo guide: [docs/RECRUITER_DEMO_CHECKLIST.md](docs/RECRUITER_DEMO_CHECKLIST.md)

## SaaS foundation (`/v1` API)

Alongside the original single-user dashboard, the backend now ships a multi-user SaaS layer:

- **Accounts & auth** — signup/login with scrypt-hashed passwords and JWT sessions (`AUTH_SECRET`); admin role bootstrapped via `ADMIN_EMAIL` and checked server-side against the database.
- **Trial & plans** — 3-day trial (`TRIAL_DAYS`), **no credit card**; server-side entitlement matrix for Free Demo / Trial / Starter / Pro / Premium; per-day usage limits (429s) and admin kill switches (`DISABLE_AI_RUNS`, `DISABLE_GMAIL_SYNC`, `DISABLE_APPLICATION_ASSIST`, `DISABLE_NEW_SIGNUPS`). Billing state changes only via the signature-verified Stripe webhook ([docs/BILLING.md](docs/BILLING.md)).
- **Data isolation** — every table keyed by `user_id`, every query filtered by the authenticated user, verified by tests. Full data export (`GET /v1/me/export`) and hard account deletion (`DELETE /v1/me`).
- **Career engine** — Career Profile onboarding, resume upload, LinkedIn paste + truthful recommendations, job validation/dedupe (canonical URL required for `Found`), deterministic fit scoring labeled as guidance, missing-skills engine over a data/AI taxonomy, teaching moments, portfolio project recommendations.
- **Gmail scaffold** — consent-first connect/disconnect, keyword event classifier, safe pipeline updates that never regress a stage and always record history ([docs/GMAIL_INTEGRATION.md](docs/GMAIL_INTEGRATION.md)).
- **Application assist (Premium scaffold)** — package builder + manual apply link + explicit "I applied" confirmation with a full audit log. **Nothing is ever submitted automatically.**
- **Admin & feedback** — `/v1/admin/*` overview (users, trials, usage, flags, failed runs) and in-app feedback capture.

Roadmap and honest scaffold status: [docs/PRODUCT_ROADMAP.md](docs/PRODUCT_ROADMAP.md) · Migration to Postgres/managed auth: [docs/SAAS_MIGRATION.md](docs/SAAS_MIGRATION.md) · Legal drafts: [docs/legal/](docs/legal/)

## Tech stack

- **Backend:** Python 3.11+, FastAPI, CrewAI, SQLite, litellm (Claude Haiku 4.5 / Sonnet)
- **Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS 4, Recharts
- **Infra:** GitHub Actions (agent cron + CI), Docker on Azure App Service, Vercel, Azure Blob Storage
- **Integrations:** Notion, Google Sheets, SMTP email, ElevenLabs TTS (optional), Serper search

## What this project demonstrates

- AI workflow orchestration (multi-agent CrewAI pipeline with task chaining and feedback loops)
- FastAPI backend design with bearer-token auth and truthful state rules
- Next.js dashboard development (Kanban pipeline, live agent monitor over WebSocket, voice UI)
- Human-in-the-loop automation — automation drafts, a human decides
- Secure API design: token auth, status-transition rules, demo/production isolation
- Cloud deployment: containerized backend on Azure, frontend on Vercel
- GitHub Actions scheduling with duplicate-run guards and failure reporting
- Data persistence and pipeline tracking (SQLite with idempotent migrations)
- Product thinking around a real daily workflow

This is a personal tool, not a production-grade product: it is single-user, uses SQLite, and has no monitoring stack. Those limitations are documented, deliberate trade-offs.

---

## Local setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt    # full agent stack
cp ../.env.example ../.env          # fill in your values
uvicorn api.main:app --reload       # API at http://localhost:8000
```

To run just the API tests (no CrewAI/integrations needed):

```bash
pip install -r requirements-ci.txt
pytest tests -q
```

To run the agent crew once locally (spends Claude API budget):

```bash
python main.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
npm run typecheck  # tsc --noEmit
npm run lint
npm run build
```

### Private profile files (git-ignored, never committed)

- `backend/config/resume.txt` — your resume text (used by the drafting agents)
- `backend/config/linkedin_profile.txt` — your LinkedIn text (used by the Monday optimizer)

In GitHub Actions these are written at run time from the `RESUME_TEXT` and `LINKEDIN_PROFILE_TEXT` repository secrets.

## Environment variables

See [.env.example](.env.example) for the full annotated list. The critical ones:

| Variable | Purpose |
|----------|---------|
| `CAREER_OS_API_TOKEN` | **Required.** Bearer token for all private API routes. Without it the API fails closed. |
| `CAREER_OS_PASSWORD` | Dashboard login password |
| `INGEST_SECRET` | Second factor for workflow → API ingest calls |
| `CAREER_OS_DB` | SQLite path. Production: a persistent mount like `/home/career-os/career_os.db` |
| `ENV` | `production` disables demo seeding routes |
| `PUBLIC_DEMO_MODE` | `true` = serve ONLY a separate sanitized demo database |
| `ALLOW_MANUAL_RUNS` | `true` enables the dashboard "Trigger Run" button (spends API budget) |
| `ALLOWED_ORIGINS` | CORS allowlist (comma-separated) |
| `ANTHROPIC_API_KEY` | Claude API for agents + interview practice |

## Security model

- **Backend:** every private route requires `Authorization: Bearer <token>` — either the static `CAREER_OS_API_TOKEN` or a session token issued by the password login. `/health` is the only public data route. The WebSocket requires the token as a query parameter.
- **Frontend:** all private pages are wrapped in an `AuthGate`; the login token is attached to every API call. Frontend gating is a UX layer — the backend enforces auth independently.
- **Automation vs. human:** ingest endpoints coerce any automated status to `Found` and never overwrite a manually-set status.
- **Demo isolation:** `PUBLIC_DEMO_MODE=true` points the API at a separate demo database seeded only with fictitious data; demo seeding routes are never registered in production.

Full details: [docs/SECURITY.md](docs/SECURITY.md).

## Production deployment

- **Backend:** Docker image built by the `Build Backend Image` workflow → GHCR → Azure App Service (B1, always-on). Set `CAREER_OS_DB=/home/career-os/career_os.db` (with App Service persistent storage enabled) so the SQLite database survives redeploys. For anything beyond single-user scale, move to Azure SQL or Postgres.
- **Frontend:** Vercel, with `NEXT_PUBLIC_API_URL` pointing at the backend.
- **Agents:** GitHub Actions cron, weekdays only, with a duplicate-run guard, concurrency group, and failure reporting to the dashboard.

The database schema is created idempotently on startup (`CREATE TABLE IF NOT EXISTS` + additive `ALTER TABLE` migrations) — redeploys never drop data.

## Public demo mode

Set `PUBLIC_DEMO_MODE=true` (backend) and `NEXT_PUBLIC_DEMO_MODE=true` (frontend) to run a recruiter-safe instance: the API serves a separate demo database, and the "Load Demo Data" button seeds fictitious companies, generic roles, and sample metrics — no private pipeline, resume, or employer-sensitive data.

## Roadmap

- Postgres/Azure SQL option for the pipeline store
- Per-stage run telemetry surfaced in the dashboard
- Browser extension to mark a job Applied at submit time
- Materials archive browser in the dashboard

## Estimated monthly cost

| Service | Cost |
|---------|------|
| Claude API | ~$3–8/month |
| Azure App Service B1 | ~$13/month |
| Serper search | Free (2,500/mo) |
| GitHub Actions | Free (2,000 min/mo) |
| Azure Blob / Kaggle / Notion | Free tiers |
