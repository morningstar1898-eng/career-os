# Gmail Integration (scaffold)

Gmail is the first and only email integration (no Outlook yet). It exists to
close the job-search feedback loop: confirmations, rejections, interviews,
recruiter outreach, assessments, offers → pipeline updates → teaching moments.

## Privacy rules (non-negotiable, enforced in code where possible)

- Explicit connect with a consent screen (`GET /v1/gmail/status` returns the
  full consent text; `POST /v1/gmail/connect` requires the Pro+ entitlement).
- Read-only scope (`gmail.readonly`), targeted job-search queries only —
  never a blind full-mailbox scan.
- Metadata/snippets first; full bodies are read only to classify a likely
  job-search email and are **never stored** — only extracted events
  (`email_events` stores sender, subject, snippet ≤500 chars, classification).
- Revocable: `POST /v1/gmail/disconnect` (clears tokens) and
  `DELETE /v1/gmail/events` (wipes imported data). Users are also pointed to
  myaccount.google.com/permissions.
- Drafts only: the app never sends email; reply drafting requires explicit
  user approval per message (future feature).
- `DISABLE_GMAIL_SYNC=true` stops all sync activity instantly.

## What is implemented now

- Connection lifecycle (status/connect/callback/disconnect) with entitlement
  + kill-switch checks and the OAuth consent URL builder.
- Keyword-based classifier (`classify_email`) with confidence scores — unit
  tested, deterministic, replaceable by an AI classifier behind the same
  signature.
- Event ingestion (`POST /v1/gmail/events/ingest`): dedupe by message id,
  application matching by company name, and **safe pipeline updates** —
  events only move an application *forward* (never regress a later stage),
  and every change lands in `application_events` history.
- Status mapping: confirmation → Confirmation Received, interview →
  Interview, recruiter → Recruiter Screen, assessment → Assessment,
  rejection → Rejected, offer → Offer (only at confidence ≥ 0.6).

## What remains to ship real Gmail sync

1. Google Cloud project: OAuth consent screen (restricted scope review is
   required for gmail.readonly in production!), client ID/secret, redirect URI.
2. Token exchange in `gmail_callback()` (code → refresh token) and encrypted
   token storage (KMS/Fernet — do not ship plaintext tokens).
3. A sync worker that runs targeted queries per user, e.g.
   `newer_than:7d (subject:(application OR interview OR assessment) OR from:(no-reply@greenhouse.io OR @lever.co OR @myworkday.com))`,
   fetches metadata format first, and feeds `/v1/gmail/events/ingest`.
4. Rate limiting is already in place (`max_email_scans_per_day` per plan).
