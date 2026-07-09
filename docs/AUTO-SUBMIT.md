# Auto-Submit — how Career OS actually submits applications

Added 2026-07-09. Career OS now has two application modes, controlled by the
**`APPLY_MODE` repository variable** (Settings → Secrets and variables → Actions → Variables):

| Mode | What happens |
|---|---|
| *(unset)* / `review` | Today's original behavior. Agents find jobs + draft materials; you apply manually. Nothing is ever submitted. |
| `auto` | After the crew runs, the `backend/auto_submit/` pipeline submits reviewer-approved applications on supported ATSs, with evidence. Everything else falls back to **Ready to Apply** with the reason in the tracker's Notes column. |

## The pipeline (auto mode)

Each job logged today goes through these gates **in order** — failing any gate
means "manual", never "guess":

1. **Hard rules** (`gating.py`) — Optum/UHG internal roles are *never*
   auto-submitted (you're a current employee; internal transfers always get
   human eyes). Duplicates (same company+role already submitted/applied) are
   skipped. Daily cap: `MAX_AUTO_SUBMITS_PER_DAY` variable, default 5.
2. **URL validation** (`ats.py`) — the posting URL is fetched for real. It must
   resolve 200, not be a closed posting, and land on a supported ATS:
   **Greenhouse, Lever, or Ashby** (public forms, no login). Workday, LinkedIn,
   Indeed, and login-walled portals cannot be auto-submitted — those jobs stay
   manual. *This also catches any URL the scout got wrong: nothing is ever
   submitted to an unverified page.*
3. **Reviewer agent** (`reviewer.py`) — a separate Sonnet model (not the Haiku
   drafter) reads the LIVE posting page + the drafted materials + your resume
   and must APPROVE: right company/role, no placeholders, no fabricated claims.
   It also extracts the exact cover-letter text to submit. Fail-closed: any
   error → held for manual review.
4. **Submission** (`submitters.py`, Playwright) — fills the form from your
   `APPLICANT_PROFILE_JSON` secret + resume PDF (pulled from private Azure
   blob). If any required field can't be answered from the profile, or a
   CAPTCHA is present, it aborts to manual — it never guesses and never
   bypasses CAPTCHAs.
5. **Evidence** — on live submit it waits for the confirmation message,
   screenshots the page, uploads the screenshot to
   `application-materials/<date>/confirmations/` in blob storage, and sets the
   Sheet row to **Submitted (auto)** with the confirmation text in Notes.
   If no confirmation is detected after clicking submit, the row says so and
   asks you to verify — the status is only Submitted when there's proof.

The **daily briefing email now ends with an "Applications Report"** section:
what was submitted (with confirmation text), what passed dry-run, and what's
waiting for you and why.

## Dry-run first (important)

`AUTO_SUBMIT_DRY_RUN` variable defaults to `true`: the pipeline does everything
*except* click Submit, and screenshots the filled form instead. Let it run 1–2
days, open the screenshots in blob storage, confirm the forms look right, then
set the variable to `false` to go live.

## Setup (one time)

Run `Setup-AutoSubmit.ps1` from the OneDrive Desktop. It:
1. Builds your applicant profile (name/email/phone/work-auth answers) and sets
   it as the `APPLICANT_PROFILE_JSON` GitHub secret (piped via stdin — never a file flag).
2. Converts your resume DOCX to PDF and uploads it to the private blob at
   `application-materials/resume/resume.pdf`.
3. Sets repo variables `APPLY_MODE=auto`, `AUTO_SUBMIT_DRY_RUN=true`,
   `MAX_AUTO_SUBMITS_PER_DAY=5`.

## Honesty guarantees (unchanged)

- Agents still only log **Found** — no agent ever claims something was applied.
- **Submitted (auto)** can only be written by the deterministic pipeline after
  a captured confirmation, and automation still can't downgrade any status you
  set manually.
- Playwright is installed only in the workflow step, so the Azure container
  image is unaffected; no container rebuild is needed to deploy this.
