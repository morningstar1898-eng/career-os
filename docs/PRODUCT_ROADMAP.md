# Product Roadmap

**Product:** a human-in-the-loop AI career operating system for data and AI
job seekers. Internal name CareerOS; external brand configurable via
`PUBLIC_APP_NAME` (final name TBD).

**The core loop:** goal → profile/resume → job discovery → fit scoring →
drafted application package → *user applies* → Gmail detects outcomes →
pipeline updates → missing skills identified → lessons/practice/portfolio
recommendations → stronger profile → better future matches.

**North-star UX question the dashboard must always answer:**
*"What should I do today to get closer to the data or AI job I want?"*

## Done (this codebase)

- ✅ Phase 0 — security + truthfulness hardening of the original app
- ✅ Phase 1 — multi-user foundation: accounts, JWT auth, per-user isolation (tested)
- ✅ Phase 2 — 3-day no-card trial, plan/entitlement matrix, usage limits, kill
  switches, Stripe webhook with signature verification (checkout = scaffold)
- ✅ Phase 3 — Career Profile API, resume upload, LinkedIn paste
- ✅ Phase 4 — job validation/dedupe, deterministic fit scoring, application
  tracker with event history, missing-skills engine, teaching moments,
  portfolio + LinkedIn recommendations
- ✅ Phase 5 — Gmail scaffold: consent, lifecycle, classifier, safe pipeline updates
- ✅ Phase 6 — Premium assist scaffold: package builder, explicit-approval
  "I applied" flow, audit log
- ✅ Phase 7 — admin overview/users/feedback/failed-runs, feedback API, legal
  docs, tests (50), CI

## Next (rough order)

1. **SaaS frontend** — signup/login, onboarding wizard, the "today" dashboard
   (trial status, next best action, matches, pipeline, gaps, teaching moments).
   The entire API exists; this is the highest-leverage gap.
2. **Stripe live** — checkout session + customer portal (docs/BILLING.md).
3. **Gmail live** — OAuth review, token exchange + encryption, sync worker
   (docs/GMAIL_INTEGRATION.md).
4. **Postgres + Alembic** (docs/SAAS_MIGRATION.md) before real users.
5. **AI enrichment** — lesson generation, resume tailoring, cover letter
   drafts behind existing entitlements/usage limits (litellm already in stack).
6. **Job discovery feeds** — adapt the existing agent crew to per-user Career
   Profiles with per-user budgets.
7. **Email verification + password reset**, session revocation.
8. **Application assist adapters** — only for sources whose terms allow it,
   always behind the explicit-approval flow.

## Explicit non-goals

- No auto-submission without per-submission user approval — ever.
- No CAPTCHA bypass, no scraping that violates job-board terms, no mass apply.
- No reading users' general email; job-search-focused queries only.
- No fake statuses: nothing is "Applied" unless the user applied.
