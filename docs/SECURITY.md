# Career OS — Security Model

## Multi-user SaaS layer (`/v1`)

- **User auth:** scrypt-hashed passwords (stdlib KDF, per-user salt, constant-time verify) + JWT sessions signed with `AUTH_SECRET` (HS256, 7-day expiry). No `AUTH_SECRET` → SaaS auth fails closed (500).
- **Data isolation:** every SaaS table carries `user_id`; every query filters by the authenticated user's id; cross-user access attempts return 404. Covered by `tests/test_saas.py`.
- **Admin:** role lives in the `users` table and is checked server-side per request (`require_admin`) — never trusted from the token payload alone or from the frontend.
- **Entitlements & billing:** plan capabilities are resolved server-side from the database (`api/saas/plans.py`); subscription state changes only via the signature-verified Stripe webhook. The frontend can never grant itself features.
- **Cost/abuse protection:** per-day usage limits (429) and kill switches (`DISABLE_AI_RUNS`, `DISABLE_GMAIL_SYNC`, `DISABLE_APPLICATION_ASSIST`, `DISABLE_NEW_SIGNUPS`).
- **Truthfulness in code:** automation can only create `Found/Saved/Drafted/Ready to Apply`; `Applied` requires an explicit user action (manual status change or the assist flow's `user_confirmed=true`), and Gmail events only move applications forward with full history in `application_events`.
- **User data rights:** full export (`GET /v1/me/export`), hard delete (`DELETE /v1/me`), Gmail disconnect + event deletion.
- **Known scaffold gaps (do not ship real users without):** email verification flow, password reset, session revocation list, encryption of Gmail refresh tokens (KMS/Fernet), Postgres instead of SQLite (docs/SAAS_MIGRATION.md).

## Private dashboard model (legacy single-user)

Career OS is a **single-user, private** system. It contains employer-sensitive information (which companies the owner is applying to), so both the repo and every deployment must stay private. There are two layers:

1. **Frontend gate (UX):** every private page is wrapped in `AuthGate` — a password prompt that exchanges `CAREER_OS_PASSWORD` for a session token.
2. **Backend enforcement (real security):** every private API route requires `Authorization: Bearer <token>`. The frontend gate alone is never trusted.

## Backend bearer token requirement

- All routes except `/health` and `/auth/*` require a bearer token (`backend/api/deps.py`).
- Two tokens are accepted, both compared with `hmac.compare_digest`:
  - the static `CAREER_OS_API_TOKEN` (workflows, server-to-server), or
  - a session token issued by `POST /auth/login`.
- If `CAREER_OS_API_TOKEN` is unset, private routes return **500 (fail closed)** — the API never silently serves data unauthenticated.
- The WebSocket (`/ws/agents`) requires the token as a `?token=` query parameter and closes with policy code 1008 otherwise.
- `/ingest/*` and `/email/briefing` additionally require `INGEST_SECRET` in the request body (defense in depth for the write path).
- `POST /runs/trigger` is further gated by `ALLOW_MANUAL_RUNS=true` because it spends real API budget.

Session tokens live in process memory and reset on redeploy; the dashboard simply re-prompts for the password. Tokens are stored in the browser's `localStorage` — an accepted trade-off for a single-user private dashboard (documented, not accidental).

## Environment variables

Secrets enter the system only through environment variables / GitHub Actions secrets. See [.env.example](../.env.example) for the full list. Key security-relevant ones: `CAREER_OS_API_TOKEN`, `CAREER_OS_PASSWORD`, `INGEST_SECRET`, `ANTHROPIC_API_KEY`, `AZURE_STORAGE_CONNECTION_STRING`, SMTP credentials, Google service-account JSON.

Generate tokens with real entropy, e.g.:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Public demo mode

`PUBLIC_DEMO_MODE=true` makes the backend serve a **separate demo database** (`CAREER_OS_DEMO_DB`) — the real database is never opened, so a demo instance cannot leak pipeline details, interview history, or run logs. Demo seeding (`/demo/seed`) fills it with fictitious companies and generic sample data, and the route is only registered outside production (or in demo mode). Frontend demo affordances are shown only when `NEXT_PUBLIC_DEMO_MODE=true` or in development.

## Sensitive files policy

Never committed (enforced via `.gitignore` and `.dockerignore`):

- `backend/config/resume.txt`, `backend/config/linkedin_profile.txt` — private profile text. In CI/cron these are written at run time from the `RESUME_TEXT` / `LINKEDIN_PROFILE_TEXT` secrets.
- `backend/config/google_credentials.json`, `kaggle.json` — service credentials.
- `.env` and all variants except `.env.example`.
- `frontend/public/*.docx|pdf` — a resume in `public/` is served to anyone with the URL; never put one there.
- `*.db` — the SQLite database contains the real pipeline.

> **History note:** `resume.txt`, `linkedin_profile.txt`, and `Meagan_Parsons_Resume.docx` existed in earlier commits. Removing them from the working tree does not remove them from git history — since the repo is private the exposure is limited, but if it is ever made public, purge history first (e.g. `git filter-repo --invert-paths --path backend/config/resume.txt --path backend/config/linkedin_profile.txt --path frontend/public/Meagan_Parsons_Resume.docx`).

## Secret handling rules

- No secrets, tokens, or private URLs hardcoded in source (the briefing email's tracker link comes from `GOOGLE_SHEET_URL`).
- Logs record run IDs, stages, and statuses — never secrets or resume/profile contents.
- Email HTML escapes all AI/web-derived text (`html.escape`) before rendering.
- Multi-line secrets are passed to workflow steps via `env:`, never inline `${{ }}` interpolation inside shell scripts.

## What should never be committed

Real API keys or tokens · the dashboard password · resume or LinkedIn text · Google/Kaggle credential files · the SQLite database · any file naming target companies or application details.

## Deployment checklist

- [ ] `CAREER_OS_API_TOKEN` set (long random value) on the App Service **and** as a GitHub secret
- [ ] `CAREER_OS_PASSWORD` set (strong, unique)
- [ ] `INGEST_SECRET` set on both sides
- [ ] `ENV=production` on the deployed backend
- [ ] `ALLOW_MANUAL_RUNS` unset (or `false`) unless actively wanted
- [ ] `PUBLIC_DEMO_MODE` unset on the private instance
- [ ] `CAREER_OS_DB=/home/career-os/career_os.db` with App Service persistent storage enabled
- [ ] `ALLOWED_ORIGINS` set to the exact Vercel URL(s), not `*`
- [ ] Repo, GHCR image, and deployments are private
- [ ] `RESUME_TEXT` / `LINKEDIN_PROFILE_TEXT` GitHub secrets populated
- [ ] Verify: `curl <api>/pipeline/` returns 401; with the token returns 200
