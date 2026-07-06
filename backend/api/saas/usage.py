"""
api/saas/usage.py
Per-user, per-day usage tracking and rate limiting — cost protection for AI
and integration features. Metrics roll up in daily buckets in usage_records.
"""
from datetime import datetime, timezone

from fastapi import HTTPException

from api.db import get_db
from api.saas import plans

# metric name → the plan limit key that caps it
METRIC_LIMITS = {
    "ai_runs": "max_ai_runs_per_day",
    "job_matches": "max_job_matches_per_day",
    "lessons": "max_ai_runs_per_day",
    "resume_tailoring": "max_ai_runs_per_day",
    "gmail_scans": "max_email_scans_per_day",
    "assist_requests": "max_ai_runs_per_day",
}


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def current_count(user_id: int, metric: str) -> int:
    with get_db() as conn:
        row = conn.execute(
            "SELECT count FROM usage_records WHERE user_id = ? AND metric = ? AND period = ?",
            (user_id, metric, _today()),
        ).fetchone()
        return row["count"] if row else 0


def check_and_increment(user: dict, metric: str, amount: int = 1):
    """Raise 429 if the user's daily limit for this metric is exhausted,
    otherwise record the usage."""
    limit_key = METRIC_LIMITS.get(metric)
    limit = plans.limit_for(user, limit_key) if limit_key else 0
    used = current_count(user["id"], metric)
    if used + amount > limit:
        raise HTTPException(
            429,
            f"Daily limit reached for {metric.replace('_', ' ')} "
            f"({limit}/day on the {plans.effective_plan(user)} plan).",
        )
    with get_db() as conn:
        conn.execute(
            "INSERT INTO usage_records (user_id, metric, period, count) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, metric, period) DO UPDATE SET count = count + ?",
            (user["id"], metric, _today(), amount, amount),
        )


def usage_summary(user_id: int) -> dict:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT metric, count FROM usage_records WHERE user_id = ? AND period = ?",
            (user_id, _today()),
        ).fetchall()
        return {r["metric"]: r["count"] for r in rows}
