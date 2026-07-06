# Billing (Stripe scaffold)

## Principles (enforced in code)

- **Webhooks are the source of truth.** Plan and subscription status only
  change via `POST /v1/billing/webhook` (signature-verified) — never from the
  frontend, never from a client-supplied field.
- **No card at signup.** The 3-day trial starts automatically; Stripe is only
  involved when the user upgrades.
- **Nothing is faked.** Without `STRIPE_SECRET_KEY`, checkout returns 501.

## What is implemented

- Webhook endpoint with Stripe v1 signature verification (stdlib HMAC,
  timestamp tolerance 5 min) and event idempotency (`billing_events` table).
- Handled events: `checkout.session.completed` (links customer → user via
  `client_reference_id = "user-<id>"`), `customer.subscription.created/updated`
  (sets plan from `STRIPE_PRICE_*` mapping + status), `customer.subscription.deleted`,
  `invoice.payment_failed` (→ past_due, grace access), `invoice.payment_succeeded`.
- Public plan catalog: `GET /v1/billing/plans`.
- Tested: signature rejection, plan upgrade via webhook, replay idempotency.

## What remains to ship billing

1. Create products/prices in Stripe; set `STRIPE_PRICE_STARTER/PRO/PREMIUM`.
2. Implement checkout-session creation in `create_checkout()` (server-side,
   `stripe` SDK or raw API): `mode=subscription`,
   `client_reference_id=f"user-{user_id}"`, success/cancel URLs.
3. Add a customer-portal session endpoint for self-serve management.
4. Point the Stripe webhook at `/v1/billing/webhook`; set `STRIPE_WEBHOOK_SECRET`.
5. Trial-ending reminder email (needs the email-sending decision first).

## Plan matrix

Defined in `backend/api/saas/plans.py` (Free Demo / Trial / Starter / Pro /
Premium). Gmail starts at Pro; application assistance is Premium-only. Limits
are per-day and enforced with 429s via `usage_records`.
