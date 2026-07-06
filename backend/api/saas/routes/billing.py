"""
Billing scaffold (Stripe). Design rules:
- Webhooks are the source of truth for subscription state — the frontend can
  never set plan or billing status.
- No credit card at signup: the 3-day trial starts automatically; Checkout is
  only used to upgrade.
- Signature verification is implemented with stdlib HMAC per Stripe's spec
  (v1 scheme), so no Stripe SDK is required for the webhook path.

Checkout-session creation returns 501 until STRIPE_SECRET_KEY is configured —
this is a deliberate scaffold, not a fake success.
"""
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from api import config
from api.db import get_db
from api.saas import plans
from api.saas.deps import get_current_user

router = APIRouter()
logger = logging.getLogger("career_os.saas.billing")

TOLERANCE_SECONDS = 300


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/billing/plans")
def list_plans():
    """Public plan catalog (entitlement matrix, no secrets)."""
    return {"plans": plans.plan_catalog(), "trial_days": config.trial_days(),
            "trial_requires_card": False}


@router.post("/billing/checkout")
def create_checkout(body: dict, user: dict = Depends(get_current_user)):
    plan = (body.get("plan") or "").strip()
    if plan not in ("starter", "pro", "premium"):
        raise HTTPException(400, "plan must be starter, pro, or premium")
    if not config.stripe_secret_key():
        raise HTTPException(
            501,
            "Billing is not configured on this deployment (STRIPE_SECRET_KEY missing). "
            "See docs/BILLING.md for setup.",
        )
    # Implementation step (documented in docs/BILLING.md): create a Stripe
    # Checkout Session server-side and return its URL. Not faked here.
    raise HTTPException(501, "Checkout session creation is scaffolded — see docs/BILLING.md.")


def verify_stripe_signature(payload: bytes, sig_header: str, secret: str) -> bool:
    """Stripe webhook v1 signature check (HMAC-SHA256 of '{t}.{payload}')."""
    try:
        parts = dict(p.split("=", 1) for p in sig_header.split(","))
        timestamp = parts.get("t", "")
        signature = parts.get("v1", "")
        if not timestamp or not signature:
            return False
        if abs(time.time() - int(timestamp)) > TOLERANCE_SECONDS:
            return False
        signed = f"{timestamp}.".encode() + payload
        expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False


@router.post("/billing/webhook")
async def stripe_webhook(request: Request):
    """Source of truth for subscription state. Rejects unsigned payloads."""
    secret = config.stripe_webhook_secret()
    if not secret:
        raise HTTPException(501, "STRIPE_WEBHOOK_SECRET not configured")

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    if not verify_stripe_signature(payload, sig, secret):
        raise HTTPException(400, "Invalid webhook signature")

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON payload")

    event_id = event.get("id", "")
    event_type = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}

    with get_db() as conn:
        # Idempotency: each Stripe event is processed once.
        dupe = conn.execute(
            "SELECT id FROM billing_events WHERE stripe_event_id = ?", (event_id,)
        ).fetchone()
        if dupe:
            return {"status": "already_processed"}
        conn.execute(
            "INSERT INTO billing_events (stripe_event_id, type, payload_summary, processed_at) "
            "VALUES (?, ?, ?, ?)",
            (event_id, event_type, json.dumps({k: obj.get(k) for k in ("id", "customer", "status")}), _now()),
        )

    handled = _apply_subscription_event(event_type, obj)
    logger.info("stripe webhook: type=%s handled=%s", event_type, handled)
    return {"status": "ok", "handled": handled}


def _plan_from_subscription(obj: dict) -> str | None:
    price_map = config.stripe_price_to_plan()
    items = ((obj.get("items") or {}).get("data")) or []
    for item in items:
        price_id = ((item.get("price") or {}).get("id")) or ""
        if price_id and price_id in price_map and price_map[price_id]:
            return price_map[price_id]
    return None


def _find_user_by_customer(conn, customer_id: str):
    if not customer_id:
        return None
    return conn.execute(
        "SELECT * FROM users WHERE stripe_customer_id = ?", (customer_id,)
    ).fetchone()


def _apply_subscription_event(event_type: str, obj: dict) -> bool:
    customer_id = obj.get("customer") or ""
    now = _now()

    with get_db() as conn:
        if event_type == "checkout.session.completed":
            # Link the Stripe customer to the user via client_reference_id.
            ref = obj.get("client_reference_id") or ""
            if ref.startswith("user-") and customer_id:
                try:
                    user_id = int(ref.replace("user-", "", 1))
                except ValueError:
                    return False
                conn.execute(
                    "UPDATE users SET stripe_customer_id = ?, updated_at = ? WHERE id = ?",
                    (customer_id, now, user_id),
                )
                return True
            return False

        user = _find_user_by_customer(conn, customer_id)
        if not user:
            return False

        if event_type in ("customer.subscription.created", "customer.subscription.updated"):
            plan = _plan_from_subscription(obj) or user["plan"]
            status = obj.get("status") or "active"
            conn.execute(
                "UPDATE users SET plan = ?, subscription_status = ?, stripe_subscription_id = ?, "
                "status = CASE WHEN ? IN ('active','trialing') THEN 'active' "
                "WHEN ? = 'past_due' THEN 'past_due' ELSE status END, updated_at = ? WHERE id = ?",
                (plan, status, obj.get("id"), status, status, now, user["id"]),
            )
            return True

        if event_type == "customer.subscription.deleted":
            conn.execute(
                "UPDATE users SET subscription_status = 'canceled', status = 'cancelled', "
                "cancelled_at = ?, updated_at = ? WHERE id = ?",
                (now, now, user["id"]),
            )
            return True

        if event_type == "invoice.payment_failed":
            conn.execute(
                "UPDATE users SET subscription_status = 'past_due', status = 'past_due', "
                "updated_at = ? WHERE id = ?",
                (now, user["id"]),
            )
            return True

        if event_type == "invoice.payment_succeeded":
            conn.execute(
                "UPDATE users SET subscription_status = 'active', status = 'active', "
                "updated_at = ? WHERE id = ?",
                (now, user["id"]),
            )
            return True

    return False
