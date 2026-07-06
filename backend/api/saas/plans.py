"""
api/saas/plans.py
Server-side plans, entitlements, and trial logic. The frontend never decides
what a user can do — every protected route resolves the user's effective plan
from the database and checks entitlements here.

Trial: 3 days (TRIAL_DAYS), no credit card. After expiry the user can still
log in, export, and delete data, but paid features return 402 until they
subscribe.
"""
from datetime import datetime, timezone

from fastapi import HTTPException

from api import config

PLAN_ORDER = ["free_demo", "trial", "starter", "pro", "premium"]

# Entitlement matrix. Limits are per-day (usage_records buckets).
PLANS = {
    "free_demo": {
        "can_upload_resume": False,
        "can_connect_gmail": False,
        "can_run_job_match": False,
        "can_generate_lessons": False,
        "can_generate_resume_tailoring": False,
        "can_use_application_assist": False,
        "max_job_matches_per_day": 0,
        "max_ai_runs_per_day": 0,
        "max_resumes": 0,
        "max_saved_jobs": 0,
        "max_email_scans_per_day": 0,
    },
    "trial": {
        "can_upload_resume": True,
        "can_connect_gmail": False,
        "can_run_job_match": True,
        "can_generate_lessons": True,
        "can_generate_resume_tailoring": True,
        "can_use_application_assist": False,
        "max_job_matches_per_day": 10,
        "max_ai_runs_per_day": 5,
        "max_resumes": 1,
        "max_saved_jobs": 25,
        "max_email_scans_per_day": 0,
    },
    "starter": {
        "can_upload_resume": True,
        "can_connect_gmail": False,
        "can_run_job_match": True,
        "can_generate_lessons": True,
        "can_generate_resume_tailoring": True,
        "can_use_application_assist": False,
        "max_job_matches_per_day": 25,
        "max_ai_runs_per_day": 10,
        "max_resumes": 3,
        "max_saved_jobs": 200,
        "max_email_scans_per_day": 0,
    },
    "pro": {
        "can_upload_resume": True,
        "can_connect_gmail": True,
        "can_run_job_match": True,
        "can_generate_lessons": True,
        "can_generate_resume_tailoring": True,
        "can_use_application_assist": False,
        "max_job_matches_per_day": 100,
        "max_ai_runs_per_day": 30,
        "max_resumes": 10,
        "max_saved_jobs": 1000,
        "max_email_scans_per_day": 24,
    },
    "premium": {
        "can_upload_resume": True,
        "can_connect_gmail": True,
        "can_run_job_match": True,
        "can_generate_lessons": True,
        "can_generate_resume_tailoring": True,
        "can_use_application_assist": True,
        "max_job_matches_per_day": 300,
        "max_ai_runs_per_day": 100,
        "max_resumes": 25,
        "max_saved_jobs": 5000,
        "max_email_scans_per_day": 96,
    },
}

ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing", "past_due"}  # past_due keeps access during grace


def _parse(dt: str | None):
    if not dt:
        return None
    try:
        parsed = datetime.fromisoformat(dt)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def trial_active(user: dict) -> bool:
    ends = _parse(user.get("trial_ends_at"))
    return bool(ends and datetime.now(timezone.utc) < ends)


def effective_plan(user: dict) -> str:
    """Resolve what the user is actually entitled to right now.

    Paid subscription (verified via Stripe webhooks) wins; otherwise an
    unexpired trial; otherwise free_demo (login allowed, paid features off).
    """
    plan = user.get("plan") or "trial"
    if user.get("status") in ("suspended", "deleted"):
        return "free_demo"
    if user.get("subscription_status") in ACTIVE_SUBSCRIPTION_STATUSES and plan in PLANS and plan != "trial":
        return plan
    if trial_active(user):
        return "trial"
    return "free_demo"


def entitlements(user: dict) -> dict:
    return dict(PLANS[effective_plan(user)])


def require_entitlement(user: dict, key: str):
    """Raise 402/403 unless the user's effective plan grants the entitlement."""
    plan = effective_plan(user)
    if not PLANS[plan].get(key, False):
        if plan == "free_demo" and not trial_active(user):
            raise HTTPException(
                402, "Your trial has ended. Subscribe to a plan to use this feature."
            )
        raise HTTPException(403, f"Your current plan ({plan}) does not include this feature.")


def limit_for(user: dict, key: str) -> int:
    return int(PLANS[effective_plan(user)].get(key, 0))


def plan_catalog() -> list[dict]:
    """Public plan listing (no secrets)."""
    return [{"name": name, **PLANS[name]} for name in PLAN_ORDER]


def new_trial_fields() -> dict:
    now = datetime.now(timezone.utc)
    from datetime import timedelta
    return {
        "trial_started_at": now.isoformat(),
        "trial_ends_at": (now + timedelta(days=config.trial_days())).isoformat(),
        "status": "trialing",
        "plan": "trial",
    }
