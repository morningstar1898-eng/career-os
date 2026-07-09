# Pre-Deploy Checklist — SaaS/Privacy WIP (committed 2026-07-06)

This branch of work locks all private API routes behind `CAREER_OS_API_TOKEN`
(fail-closed), moves private profile files out of the repo into GitHub Actions
secrets, and adds the multi-user SaaS layer under `/v1`. **Deploying without
the steps below breaks the live dashboard and daily briefing.** Reviewed
2026-07-06 (all 50 tests passing; no secrets in tree; see findings at bottom).

## 1. BEFORE pushing to GitHub (owner: Meagan)

- [ ] Run `OneDrive\Desktop\Update-CareerOS-Resume.ps1` — sets the
      `RESUME_TEXT` repo secret from the corrected local resume (and commits
      the corrected resume.txt to the remote, which this WIP then removes).
- [x] Set the LinkedIn profile secret (done 2026-07-07). NOTE: `gh secret set`
      has NO `--body-file` flag — pipe the content via stdin instead:
      `git show master:backend/config/linkedin_profile.txt | gh secret set LINKEDIN_PROFILE_TEXT --repo morningstar1898-eng/career-os`
      (A failed file read still creates an EMPTY secret with no error — verify with `gh secret list`.)
- [ ] Generate one long random token and set it BOTH places:
      - GitHub: `gh secret set CAREER_OS_API_TOKEN --repo morningstar1898-eng/career-os`
      - Azure:  `az webapp config appsettings set -n career-os-api -g career-os-rg --settings CAREER_OS_API_TOKEN=<same value>`
      (Verified 2026-07-06: this secret does NOT exist yet in GitHub.)

## 2. BEFORE restarting the container (Azure app settings)

- [ ] `CAREER_OS_API_TOKEN` — see above (all private routes 500 without it).
- [ ] `AUTH_SECRET` — long random string; SaaS `/v1` auth is disabled without it.
- [ ] `ADMIN_EMAIL` — Meagan's email, so her signup gets the admin role.
- [ ] `ALLOW_MANUAL_RUNS=true` — ONLY if the dashboard "Trigger Run" button
      should keep working (it now 403s by default as a cost guard).
- [ ] Confirm CORS: legacy `CORS_ORIGINS` still works as fallback, but prefer
      setting `ALLOWED_ORIGINS=https://career-os-beta-gray.vercel.app`.
- [ ] Stripe/Gmail vars stay EMPTY until those features are really configured
      (endpoints return honest 501s meanwhile).

## 3. Deploy order

1. Complete sections 1–2.
2. Push master (workflow + backend land together).
3. `gh workflow run build-backend-image.yml --repo morningstar1898-eng/career-os`
4. `az webapp restart -n career-os-api -g career-os-rg`
5. Verify with the token:
   `curl -H "Authorization: Bearer <token>" https://career-os-api.azurewebsites.net/briefings/history`
   plus `/health` (public) and a dashboard login in the browser.
6. Update the `career-os-daily-check` scheduled agent: `/briefings/today` is no
   longer public — its verification curl needs the bearer header now.

## 4. Fixes the next session should make (from the 2026-07-06 review)

- [ ] **Gmail callback honesty:** `POST /v1/gmail/callback` records
      `status='connected'` without exchanging the OAuth code. Use a `pending`
      status until real token exchange exists (update tests accordingly).
      Rule: stubbed ≠ connected — no fake successes.
- [ ] `backend/run.sh` (obsolete Oryx locator script) was deleted 2026-07-06 —
      do not resurrect it; the Docker CMD is the only startup path.
- [ ] **Weekend runs:** crons changed to weekdays-only (`1-5`). Confirm with
      Meagan whether Saturday/Sunday briefings should return.
- [ ] Add basic rate limiting to `/v1/auth/login` and `/v1/auth/signup`
      (scrypt slows brute force but doesn't stop it).
- [ ] Encrypt `gmail_connections.refresh_token` before any real token is ever
      stored (column is plaintext TEXT; currently always NULL).
- [ ] Replace deprecated `datetime.utcnow()` calls (50 warnings in tests).
- [ ] Note: WebSocket auth token travels in the query string (browser
      limitation) — keep it out of any request logging.

## 5. History note

The privacy pass removes `resume.txt`, `linkedin_profile.txt`, and the resume
.docx from the tree, but they remain in **git history**. The repo must stay
private; a `git filter-repo` scrub is optional hardening if it ever goes public.
