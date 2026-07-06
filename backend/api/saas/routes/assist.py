"""
Higher-tier application assistance — the SAFE MVP.

What it does: builds an application package (checklist, tailored-material
placeholders, the manual apply link) and records an explicit, user-confirmed
"I applied" action. Every action lands in the audit log.

What it deliberately does NOT do: submit anything anywhere. Direct submission
would be adapter-based, per-site, terms-compliant, and gated behind the same
explicit-confirmation flow — none of which exists yet, and nothing here
pretends it does. No CAPTCHA bypass, no mass apply, ever.
"""
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api import config
from api.db import get_db
from api.saas import plans, usage
from api.saas.deps import get_current_user
from api.saas.routes.jobs import record_event

router = APIRouter()
logger = logging.getLogger("career_os.saas.assist")


class PackageRequest(BaseModel):
    application_id: int
    resume_id: int | None = None


class ConfirmAppliedRequest(BaseModel):
    application_id: int
    user_confirmed: bool = False
    notes: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audit(conn, user_id: int, action: str, application_id=None, job_id=None,
           user_confirmed=False, payload_summary="", result="", error_message=""):
    conn.execute(
        "INSERT INTO assist_audit_log (user_id, application_id, job_id, action, user_confirmed, "
        "payload_summary, result, error_message, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, application_id, job_id, action, 1 if user_confirmed else 0,
         payload_summary[:500], result[:200], error_message[:500], _now()),
    )


def _check_enabled(user: dict):
    plans.require_entitlement(user, "can_use_application_assist")
    if config.disable_application_assist():
        raise HTTPException(503, "Application assistance is temporarily disabled by the administrator.")


@router.post("/assist/package")
def build_application_package(req: PackageRequest, user: dict = Depends(get_current_user)):
    """Build a review-ready application package. Nothing is submitted."""
    _check_enabled(user)
    usage.check_and_increment(user, "assist_requests")

    with get_db() as conn:
        app = conn.execute(
            "SELECT a.*, j.company, j.role, j.canonical_url, j.required_skills, j.id AS jid "
            "FROM saas_applications a JOIN saas_jobs j ON a.job_id = j.id "
            "WHERE a.id = ? AND a.user_id = ?",
            (req.application_id, user["id"]),
        ).fetchone()
        if not app:
            raise HTTPException(404, "Application not found")

        resume = None
        if req.resume_id:
            resume = conn.execute(
                "SELECT id, name, version FROM resumes WHERE id = ? AND user_id = ?",
                (req.resume_id, user["id"]),
            ).fetchone()
            if not resume:
                raise HTTPException(404, "Resume not found")

        required = json.loads(app["required_skills"] or "[]")
        package = {
            "company": app["company"],
            "role": app["role"],
            "apply_link": app["canonical_url"],
            "resume_version": dict(resume) if resume else None,
            "checklist": [
                "Review the tailored resume bullets against the posting",
                "Review the cover letter draft — verify every claim is true",
                "Answer any application questions in your own words",
                "Open the apply link and submit the application YOURSELF",
                "Come back and press 'I applied' so the tracker updates",
            ],
            "tailoring_targets": required[:10],
            "cover_letter_draft": None,   # generated via /v1/... AI tailoring when enabled
            "resume_bullets_draft": None,
            "submission": "manual — this product does not submit applications for you",
        }

        conn.execute(
            "UPDATE saas_applications SET status = CASE WHEN status IN ('Found','Saved') "
            "THEN 'Ready to Apply' ELSE status END, resume_version_id = COALESCE(?, resume_version_id), "
            "updated_at = ? WHERE id = ? AND user_id = ?",
            (req.resume_id, _now(), req.application_id, user["id"]),
        )
        _audit(conn, user["id"], "package_built", req.application_id, app["jid"],
               user_confirmed=False,
               payload_summary=f"{app['company']} / {app['role']}", result="ok")

    return {"status": "ok", "package": package}


@router.post("/assist/confirm-applied")
def confirm_applied(req: ConfirmAppliedRequest, user: dict = Depends(get_current_user)):
    """The explicit human approval step. Only proceeds when user_confirmed is
    literally true — this is what moves an application to Applied."""
    _check_enabled(user)
    if not req.user_confirmed:
        with get_db() as conn:
            _audit(conn, user["id"], "confirm_applied_rejected", req.application_id,
                   user_confirmed=False, result="refused",
                   error_message="user_confirmed was not true")
        raise HTTPException(400, "Explicit confirmation required: set user_confirmed=true "
                                 "only after you actually submitted the application.")

    now = _now()
    with get_db() as conn:
        app = conn.execute(
            "SELECT * FROM saas_applications WHERE id = ? AND user_id = ?",
            (req.application_id, user["id"]),
        ).fetchone()
        if not app:
            raise HTTPException(404, "Application not found")
        conn.execute(
            "UPDATE saas_applications SET status = 'Applied', application_date = COALESCE(application_date, ?), "
            "last_event_date = ?, notes = COALESCE(?, notes), updated_at = ? WHERE id = ? AND user_id = ?",
            (now[:10], now, req.notes, now, req.application_id, user["id"]),
        )
        record_event(conn, user["id"], req.application_id, "status_change",
                     app["status"], "Applied", "assist", "user confirmed manual submission")
        _audit(conn, user["id"], "confirm_applied", req.application_id, app["job_id"],
               user_confirmed=True, result="applied")
    logger.info("assist confirm-applied: user_id=%s application_id=%s", user["id"], req.application_id)
    return {"status": "ok", "new_status": "Applied"}


@router.get("/assist/audit")
def my_assist_audit(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM assist_audit_log WHERE user_id = ? ORDER BY id DESC LIMIT 100",
            (user["id"],),
        ).fetchall()
        return [dict(r) for r in rows]
