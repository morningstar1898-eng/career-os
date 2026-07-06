# SaaS Migration Guide

How the private single-user CareerOS becomes a multi-user SaaS — what exists
now, and the path to production scale.

## What exists now (implemented)

- **Two API surfaces on one backend:**
  - Legacy single-user routes (`/briefings`, `/pipeline`, `/runs`, …) — static
    bearer token, unchanged, still power the private dashboard and daily cron.
  - SaaS routes under **`/v1`** — per-user JWT sessions, plans, entitlements,
    usage limits, per-user data isolation.
- **Users**: scrypt password hashing, JWT sessions (`AUTH_SECRET`), roles
  (user/admin via `ADMIN_EMAIL` bootstrap), statuses
  (active/trialing/past_due/cancelled/suspended/deleted).
- **Isolation**: every SaaS table carries `user_id`; every query filters by the
  authenticated user; covered by tests (`tests/test_saas.py`).
- **Trial**: 3 days (`TRIAL_DAYS`), no card. Expired trial → `free_demo`
  entitlements (login/export/delete still work; paid features return 402).
- **Entitlements & usage**: server-side plan matrix (`api/saas/plans.py`),
  daily usage buckets + 429 limits (`api/saas/usage.py`), kill switches.

## Database: SQLite now → Postgres for production

SQLite (via `CAREER_OS_DB`) is fine for development and the single-owner
deployment. **Real multi-user production must move to Postgres** (Azure
Database for PostgreSQL, Supabase, Neon, RDS):

1. Set `DATABASE_URL=postgresql://...` (config hook already exists).
2. Introduce SQLAlchemy models mirroring `api/saas/schema.py` (the DDL is
   deliberately portable: INTEGER PKs, TEXT/ISO dates, JSON-in-TEXT columns
   become `jsonb`).
3. Add Alembic; the initial revision is a transcription of `schema.py`.
4. Swap `api/db.py`'s connection factory for an engine/session factory behind
   the same `get_db()` interface — routes use plain SQL through one choke
   point, so the surface area is small.
5. One-time data copy: export SQLite tables → `COPY` into Postgres.

Why not now: doing it mid-feature would have coupled a risky infra change to
feature work. The query layer is centralized so the swap is mechanical.

## Auth: why backend JWT (and when to switch)

Chosen: backend-issued JWT sessions with scrypt password hashing — standard
algorithms (PyJWT HS256, stdlib scrypt), no vendor lock-in, works with the
existing FastAPI + Next.js split, fully testable offline.

Graduate to **Auth.js (NextAuth) or Clerk/Auth0** when you need: OAuth social
login, email verification flows at volume, MFA, or session revocation lists.
The user table already stores `email_verified` and provider-agnostic fields so
a managed provider can slot in (map `provider_id` → `users.id`).

Known scaffold gaps (documented, not hidden):
- Email verification is stored but not enforced (no verification emails yet).
- JWTs are stateless — logout is client-side until a revocation list exists.
- Gmail refresh tokens would be stored in the DB column as-is; encrypt with a
  KMS/Fernet key before the real token exchange ships.

## Deployment shape at SaaS scale

- Backend container (as today) + Postgres + a worker for Gmail sync/AI runs
  (the GitHub-Actions cron pattern doesn't fit per-user schedules — move to a
  queue or APScheduler/Celery worker).
- Per-user AI budgets are already modeled by usage limits; enforce spend
  alerts via the admin overview.
