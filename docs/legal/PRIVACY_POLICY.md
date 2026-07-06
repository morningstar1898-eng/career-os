# Privacy Policy (draft — review with counsel before public launch)

_Applies to the SaaS product (internal name CareerOS; display name set by PUBLIC_APP_NAME)._

## What we store, and why

- **Account data**: email, hashed password (scrypt — we cannot read it), role, plan, trial and subscription state.
- **Career data you give us**: Career Profile answers, resume text, pasted LinkedIn content, portfolio links. Used only to match jobs, score fit, find skill gaps, and draft materials for you.
- **Job & application data**: jobs you save, application statuses, event history.
- **Gmail-derived events** (only if you explicitly connect Gmail): extracted job-search events — sender, subject, a short snippet, and a classification. We do not store full email bodies.
- **Usage records**: daily counts of AI/matching features, for plan limits and cost control.
- **Feedback** you submit.

## What we do NOT do

- We do not sell your data.
- We do not read your general email; Gmail access is read-only, job-search-focused, and optional.
- We do not send emails or submit applications on your behalf without your explicit approval of each action.
- We do not show your data to other users. Every record is isolated to your account and every query is filtered by your authenticated user ID.
- We do not use your private data in public demos (demo mode runs on a separate, fictitious dataset).

## Your controls

- **Export** everything: `GET /v1/me/export`.
- **Delete your account and all data**: `DELETE /v1/me` (immediate hard delete of career data; account row anonymized).
- **Delete your resume(s)** or pasted LinkedIn content individually.
- **Disconnect Gmail** at any time and **delete all imported email events**.
- Cancel your subscription via the billing portal.

## Retention

Data is retained while your account is active. Deletion requests take effect immediately in the application database. Backups age out on the backup schedule documented in operations docs.

## Security

Bearer/JWT authentication on every private route, scrypt password hashing, secrets only in environment variables, no private content in logs. See docs/SECURITY.md.
