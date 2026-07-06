"""
Admin-only routes (role checked against the users table server-side) plus the
in-app feedback endpoint for regular users. No secrets, resume text, or email
bodies ever appear in admin views.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api import config
from api.db import get_db
from api.saas import plans
from api.saas.deps import get_current_user, require_admin

router = APIRouter()

FEEDBACK_AREAS = [
    "job_match", "skill_gap", "lesson", "linkedin_rec", "resume_rec",
    "job_rejected_reason", "interview_prep", "general",
]


class FeedbackRequest(BaseModel):
    area: str
    target_id: int | None = None
    rating: str | None = None       # useful | not_useful | inaccurate | other
    comment: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Feedback (any authenticated user) ─────────────────────

@router.post("/feedback")
def submit_feedback(req: FeedbackRequest, user: dict = Depends(get_current_user)):
    if req.area not in FEEDBACK_AREAS:
        raise HTTPException(400, f"area must be one of: {FEEDBACK_AREAS}")
    with get_db() as conn:
        conn.execute(
            "INSERT INTO feedback (user_id, area, target_id, rating, comment, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user["id"], req.area, req.target_id, req.rating, (req.comment or "")[:2000], _now()),
        )
    return {"status": "ok"}


# ── Admin dashboard ───────────────────────────────────────

@router.get("/admin/overview")
def admin_overview(admin: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        def one(sql, *args):
            return conn.execute(sql, args).fetchone()[0]

        total_users = one("SELECT COUNT(*) FROM users WHERE status != 'deleted'")
        active_trials = one(
            "SELECT COUNT(*) FROM users WHERE status = 'trialing' AND trial_ends_at > ?", now)
        expired_trials = one(
            "SELECT COUNT(*) FROM users WHERE status = 'trialing' AND trial_ends_at <= ?", now)
        active_subs = one(
            "SELECT COUNT(*) FROM users WHERE subscription_status IN ('active','trialing')")
        cancelled = one("SELECT COUNT(*) FROM users WHERE status = 'cancelled'")
        gmail_connected = one("SELECT COUNT(*) FROM gmail_connections WHERE status = 'connected'")
        failed_runs = one("SELECT COUNT(*) FROM runs WHERE status = 'failed'")
        feedback_count = one("SELECT COUNT(*) FROM feedback")
        assist_actions = one("SELECT COUNT(*) FROM assist_audit_log")
        usage_today = conn.execute(
            "SELECT metric, SUM(count) AS total FROM usage_records WHERE period = ? GROUP BY metric",
            (datetime.now(timezone.utc).strftime("%Y-%m-%d"),),
        ).fetchall()

    return {
        "users": {"total": total_users, "active_trials": active_trials,
                  "expired_trials": expired_trials, "active_subscriptions": active_subs,
                  "cancelled": cancelled},
        "integrations": {"gmail_connections": gmail_connected},
        "runs": {"failed": failed_runs},
        "assist_actions": assist_actions,
        "feedback_submissions": feedback_count,
        "usage_today": {r["metric"]: r["total"] for r in usage_today},
        "feature_flags": {
            "DISABLE_AI_RUNS": config.disable_ai_runs(),
            "DISABLE_GMAIL_SYNC": config.disable_gmail_sync(),
            "DISABLE_APPLICATION_ASSIST": config.disable_application_assist(),
            "DISABLE_NEW_SIGNUPS": config.disable_new_signups(),
            "PUBLIC_DEMO_MODE": config.public_demo_mode(),
        },
        "trial_days": config.trial_days(),
    }


@router.get("/admin/users")
def admin_users(admin: dict = Depends(require_admin), limit: int = 100):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, email, role, status, plan, subscription_status, trial_ends_at, "
            "created_at, last_login_at FROM users ORDER BY id DESC LIMIT ?",
            (min(limit, 500),),
        ).fetchall()
        users = []
        for r in rows:
            d = dict(r)
            d["effective_plan"] = plans.effective_plan(d)
            users.append(d)
        return users


@router.get("/admin/feedback")
def admin_feedback(admin: dict = Depends(require_admin), limit: int = 200):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM feedback ORDER BY id DESC LIMIT ?", (min(limit, 1000),),
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/admin/failed-runs")
def admin_failed_runs(admin: dict = Depends(require_admin), limit: int = 50):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, started_at, finished_at, status, stage, error_message, trigger "
            "FROM runs WHERE status = 'failed' ORDER BY id DESC LIMIT ?",
            (min(limit, 200),),
        ).fetchall()
        return [dict(r) for r in rows]
