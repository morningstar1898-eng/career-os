"""
User-scoped job discovery, validation, fit scoring, and the application
tracker with full event history.

Truthfulness rules (enforced here, not just prompted):
- A job is only `verified` / eligible for Found with a canonical URL.
- Automation and assist flows can only create Found/Saved/Drafted/Ready to Apply.
- Only the user (manual) or a confirmed Gmail event moves an application to
  Applied / Confirmation Received / beyond — and every change is recorded in
  application_events.
- Fit scores are labeled guidance, not guarantees.
"""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.db import get_db
from api.saas import plans, usage
from api.saas.deps import get_current_user
from api.saas.routes.profile import get_profile_row
from api.saas.skills_data import extract_skills

router = APIRouter()

APPLICATION_STATUSES = [
    "Found", "Saved", "Drafted", "Ready to Apply",
    "Applied", "Confirmation Received", "Recruiter Screen", "Assessment",
    "Interview", "Offer", "Rejected", "Ghosted", "Withdrawn",
]
AUTOMATION_STATUSES = {"Found", "Saved", "Drafted", "Ready to Apply"}
GMAIL_EVENT_STATUSES = {
    "Confirmation Received", "Recruiter Screen", "Assessment",
    "Interview", "Offer", "Rejected",
}


class JobCreate(BaseModel):
    company: str
    role: str
    canonical_url: str | None = None
    source: str | None = None
    location: str | None = None
    remote_type: str | None = None
    salary_text: str | None = None
    employment_type: str | None = None
    description: str | None = None
    required_skills: list[str] | None = None
    preferred_skills: list[str] | None = None


class StatusChange(BaseModel):
    status: str
    notes: str | None = None
    outcome_reason: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _has_url(url: str | None) -> bool:
    return bool(url) and url.strip().lower().startswith(("http://", "https://"))


def record_event(conn, user_id: int, application_id: int, event_type: str,
                 from_status: str | None, to_status: str | None, source: str, detail: str = ""):
    conn.execute(
        "INSERT INTO application_events (user_id, application_id, event_type, from_status, "
        "to_status, source, detail, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, application_id, event_type, from_status, to_status, source, detail[:1000], _now()),
    )


# ── Jobs ──────────────────────────────────────────────────

@router.post("/jobs")
def create_job(req: JobCreate, user: dict = Depends(get_current_user)):
    company, role = req.company.strip(), req.role.strip()
    if not company or not role:
        raise HTTPException(400, "company and role are required")

    max_saved = plans.limit_for(user, "max_saved_jobs")
    url = (req.canonical_url or "").strip() or None
    dup_key = f"{company.lower()}|{role.lower()}|{(url or '').lower()}"
    validation = "verified" if _has_url(url) else "unverified"

    required = req.required_skills or extract_skills(req.description or "")
    preferred = req.preferred_skills or []

    with get_db() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM saas_jobs WHERE user_id = ?", (user["id"],)
        ).fetchone()[0]
        if count >= max_saved:
            raise HTTPException(403, f"Your plan allows up to {max_saved} saved jobs.")

        existing = conn.execute(
            "SELECT id FROM saas_jobs WHERE user_id = ? AND duplicate_key = ?",
            (user["id"], dup_key),
        ).fetchone()
        if existing:
            return {"status": "duplicate", "job_id": existing["id"],
                    "validation_status": "duplicate"}

        cursor = conn.execute(
            "INSERT INTO saas_jobs (user_id, company, role, canonical_url, source, date_found, "
            "location, remote_type, salary_text, employment_type, description, required_skills, "
            "preferred_skills, validation_status, duplicate_key, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user["id"], company, role, url, req.source, _now()[:10], req.location,
             req.remote_type, req.salary_text, req.employment_type, req.description,
             json.dumps(required), json.dumps(preferred), validation, dup_key, _now()),
        )
        job_id = cursor.lastrowid

        # A tracker record starts as Found only when the posting is verified;
        # unverified postings start as Saved (the user found it, but it lacks a canonical URL).
        initial_status = "Found" if validation == "verified" else "Saved"
        app_cursor = conn.execute(
            "INSERT INTO saas_applications (user_id, job_id, status, source, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user["id"], job_id, initial_status, req.source, _now()),
        )
        record_event(conn, user["id"], app_cursor.lastrowid, "status_change",
                     None, initial_status, "automation", f"job logged ({validation})")

    return {"status": "ok", "job_id": job_id, "application_id": app_cursor.lastrowid,
            "validation_status": validation, "initial_status": initial_status}


@router.get("/jobs")
def list_jobs(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, company, role, canonical_url, source, date_found, location, remote_type, "
            "salary_text, validation_status, overall_fit_score, created_at "
            "FROM saas_jobs WHERE user_id = ? ORDER BY id DESC",
            (user["id"],),
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/jobs/{job_id}")
def get_job(job_id: int, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM saas_jobs WHERE id = ? AND user_id = ?", (job_id, user["id"]),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Job not found")
        d = dict(row)
        for f in ("required_skills", "preferred_skills"):
            try:
                d[f] = json.loads(d[f]) if d[f] else []
            except (json.JSONDecodeError, TypeError):
                d[f] = []
        if d.get("fit_details"):
            try:
                d["fit_details"] = json.loads(d["fit_details"])
            except json.JSONDecodeError:
                pass
        return d


# ── Fit scoring (deterministic, labeled as guidance) ─────

@router.post("/jobs/{job_id}/score")
def score_job(job_id: int, user: dict = Depends(get_current_user)):
    plans.require_entitlement(user, "can_run_job_match")
    usage.check_and_increment(user, "job_matches")

    with get_db() as conn:
        job = conn.execute(
            "SELECT * FROM saas_jobs WHERE id = ? AND user_id = ?", (job_id, user["id"]),
        ).fetchone()
    if not job:
        raise HTTPException(404, "Job not found")
    profile_row = get_profile_row(user["id"])
    if not profile_row:
        raise HTTPException(400, "Complete your Career Profile first")
    profile = dict(profile_row)

    with get_db() as conn:
        resume = conn.execute(
            "SELECT content FROM resumes WHERE user_id = ? ORDER BY version DESC LIMIT 1",
            (user["id"],),
        ).fetchone()
    resume_text = (resume["content"] if resume else "").lower()

    user_skills = {s.lower() for s in json.loads(profile.get("current_skills") or "[]")}
    required = json.loads(job["required_skills"] or "[]")
    preferred = json.loads(job["preferred_skills"] or "[]")

    def match_pct(skills: list[str]) -> tuple[float, list, list]:
        if not skills:
            return 1.0, [], []
        hit = [s for s in skills if s.lower() in user_skills or s.lower() in resume_text]
        missed = [s for s in skills if s not in hit]
        return len(hit) / len(skills), hit, missed

    req_pct, req_hit, req_miss = match_pct(required)
    pref_pct, pref_hit, _ = match_pct(preferred)

    resume_alignment = 0.0
    if resume_text and required:
        resume_alignment = len([s for s in required if s.lower() in resume_text]) / len(required)

    targets = [t.lower() for t in json.loads(profile.get("target_roles") or "[]")]
    role_low = job["role"].lower()
    seniority_fit = 1.0 if any(t in role_low or role_low in t for t in targets) else 0.5 if targets else 0.5

    locations = [loc.lower() for loc in json.loads(profile.get("target_locations") or "[]")]
    job_loc = (job["location"] or "").lower()
    remote_ok = (profile.get("remote_preference") or "").lower() in ("remote", "any", "flexible") \
        and (job["remote_type"] or "").lower() in ("remote", "hybrid")
    location_fit = 1.0 if (remote_ok or not job_loc or any(l in job_loc for l in locations)) else 0.4

    portfolio_alignment = 0.5 if profile.get("portfolio_links") or profile.get("github_url") else 0.0

    overall = round(
        0.40 * req_pct + 0.10 * pref_pct + 0.20 * resume_alignment +
        0.15 * seniority_fit + 0.10 * location_fit + 0.05 * portfolio_alignment,
        3,
    )

    details = {
        "overall_fit_score": overall,
        "skill_match_score": round(req_pct, 3),
        "preferred_match_score": round(pref_pct, 3),
        "resume_alignment_score": round(resume_alignment, 3),
        "portfolio_alignment_score": portfolio_alignment,
        "seniority_fit": seniority_fit,
        "location_fit": location_fit,
        "salary_fit": None,  # scored only when structured salary data exists
        "matched_required_skills": req_hit,
        "missing_required_skills": req_miss,
        "matched_preferred_skills": pref_hit,
        "reasoning_summary": (
            f"Matched {len(req_hit)}/{len(required)} required skills"
            + (f"; biggest gaps: {', '.join(req_miss[:5])}" if req_miss else "")
            + ". This score is guidance based on keyword and profile comparison — not a guarantee of fit or outcome."
        ),
        "disclaimer": "Guidance only — review the posting yourself before applying.",
    }

    with get_db() as conn:
        conn.execute(
            "UPDATE saas_jobs SET overall_fit_score = ?, fit_details = ?, updated_at = ? "
            "WHERE id = ? AND user_id = ?",
            (overall, json.dumps(details), _now(), job_id, user["id"]),
        )
    return details


# ── Application tracker ───────────────────────────────────

@router.get("/applications")
def list_applications(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT a.*, j.company, j.role, j.canonical_url, j.validation_status "
            "FROM saas_applications a LEFT JOIN saas_jobs j ON a.job_id = j.id "
            "WHERE a.user_id = ? ORDER BY a.id DESC",
            (user["id"],),
        ).fetchall()
        return [dict(r) for r in rows]


@router.patch("/applications/{app_id}/status")
def change_status(app_id: int, req: StatusChange, user: dict = Depends(get_current_user)):
    """Manual status change by the authenticated user — the ONLY path that can
    set Applied (besides a confirmed Gmail event or an explicit assist
    confirmation, both of which also record history)."""
    if req.status not in APPLICATION_STATUSES:
        raise HTTPException(400, f"Status must be one of: {APPLICATION_STATUSES}")
    now = _now()
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM saas_applications WHERE id = ? AND user_id = ?",
            (app_id, user["id"]),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Application not found")
        conn.execute(
            "UPDATE saas_applications SET status = ?, last_event_date = ?, "
            "application_date = COALESCE(application_date, CASE WHEN ? = 'Applied' THEN ? END), "
            "notes = COALESCE(?, notes), outcome_reason = COALESCE(?, outcome_reason), updated_at = ? "
            "WHERE id = ? AND user_id = ?",
            (req.status, now, req.status, now[:10], req.notes, req.outcome_reason, now, app_id, user["id"]),
        )
        record_event(conn, user["id"], app_id, "status_change",
                     row["status"], req.status, "manual", req.notes or "")
    return {"status": "ok", "application_id": app_id, "new_status": req.status}


@router.get("/applications/{app_id}/events")
def application_events(app_id: int, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        app = conn.execute(
            "SELECT id FROM saas_applications WHERE id = ? AND user_id = ?",
            (app_id, user["id"]),
        ).fetchone()
        if not app:
            raise HTTPException(404, "Application not found")
        rows = conn.execute(
            "SELECT * FROM application_events WHERE application_id = ? AND user_id = ? ORDER BY id",
            (app_id, user["id"]),
        ).fetchall()
        return [dict(r) for r in rows]
