import os
import json
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from api.db import get_db

router = APIRouter()
logger = logging.getLogger("career_os.ingest")

# Automation may only create these statuses. "Applied" (and everything after
# it) is reserved for a manual user action — the system never claims an
# application was submitted when it wasn't. "Submitted (auto)" is the one
# exception: the auto_submit pipeline sets it ONLY after a live submission
# with a captured confirmation page (evidence blob linked in notes).
AUTOMATION_STATUSES = {"Found", "Saved", "Drafted", "Ready to Apply", "Submitted (auto)"}
MANUAL_STATUSES = {
    "Applied", "Confirmation Received", "Recruiter Screen", "Assessment",
    "Phone Screen", "Interview", "Offer", "Rejected", "Ghosted", "Withdrawn",
}


class IngestRequest(BaseModel):
    secret: str
    crew_output: str
    jobs_found: int = 0
    # Legacy field name kept for backward compatibility with older workflow
    # versions; treated as jobs_found, never as submitted applications.
    jobs_applied: int = 0
    skills_gap_count: int = 0
    portfolio_items: int = 0


class RunFailureRequest(BaseModel):
    secret: str
    stage: str = "unknown"
    error_message: str = ""
    trigger: str = "cron"


class ApplicationItem(BaseModel):
    date_applied: str
    company: str
    role: str
    url: Optional[str] = None
    status: str = "Found"
    notes: Optional[str] = None
    blob_url: Optional[str] = None
    source: Optional[str] = None


class ApplicationsIngestRequest(BaseModel):
    secret: str
    applications: List[ApplicationItem]


def _check_secret(secret: str):
    expected = os.getenv("INGEST_SECRET", "")
    if not expected or secret != expected:
        raise HTTPException(403, "Invalid secret")


def _has_canonical_url(url: Optional[str]) -> bool:
    return bool(url) and url.strip().lower().startswith(("http://", "https://"))


@router.post("/crew-result")
def ingest_crew_result(req: IngestRequest):
    _check_secret(req.secret)

    today = datetime.utcnow().strftime("%Y-%m-%d")
    now = datetime.utcnow().isoformat()
    jobs_found = req.jobs_found or req.jobs_applied

    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO runs (started_at, finished_at, status, trigger, stage) VALUES (?, ?, 'success', 'cron', 'done')",
            (now, now),
        )
        run_id = cursor.lastrowid

        content = json.dumps({"raw_output": req.crew_output})
        conn.execute(
            "INSERT OR REPLACE INTO briefings (run_id, date, content_json) VALUES (?, ?, ?)",
            (run_id, today, content),
        )

        # metrics.jobs_applied is a legacy column name — it stores jobs FOUND
        # by the agents (the UI labels it truthfully).
        conn.execute(
            "INSERT INTO metrics (date, jobs_applied, skills_gap_count, interview_score, portfolio_items) VALUES (?, ?, ?, 0, ?)",
            (today, jobs_found, req.skills_gap_count, req.portfolio_items),
        )

    logger.info("crew result ingested: run_id=%s jobs_found=%s", run_id, jobs_found)
    return {"status": "ok", "run_id": run_id, "date": today}


@router.post("/run-failure")
def ingest_run_failure(req: RunFailureRequest):
    """Record a failed agent run (called by the workflow's failure handler)."""
    _check_secret(req.secret)
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO runs (started_at, finished_at, status, trigger, stage, error_message) "
            "VALUES (?, ?, 'failed', ?, ?, ?)",
            (now, now, req.trigger, req.stage[:100], req.error_message[:500]),
        )
        run_id = cursor.lastrowid
    logger.warning("run failure recorded: run_id=%s stage=%s", run_id, req.stage)
    return {"status": "ok", "run_id": run_id}


@router.post("/applications")
def ingest_applications(req: ApplicationsIngestRequest):
    _check_secret(req.secret)
    if not req.applications:
        return {"status": "ok", "upserted": 0, "skipped": 0}

    now = datetime.utcnow().isoformat()
    upserted = 0
    skipped = 0
    with get_db() as conn:
        for item in req.applications:
            company = (item.company or "").strip()
            role = (item.role or "").strip()
            if not company or not role:
                skipped += 1
                continue

            # Automation can never set Applied (or any manual status).
            status = item.status if item.status in AUTOMATION_STATUSES else "Found"
            validation_status = "verified" if _has_canonical_url(item.url) else "unverified"
            url = (item.url or "").strip() or None

            # Duplicate detection: company + role + canonical URL, falling
            # back to company + role + date for URL-less rows.
            existing = None
            if url:
                existing = conn.execute(
                    "SELECT id, status FROM applications WHERE company = ? AND role = ? AND url = ?",
                    (company, role, url),
                ).fetchone()
            if not existing:
                existing = conn.execute(
                    "SELECT id, status FROM applications WHERE company = ? AND role = ? AND date_applied = ?",
                    (company, role, item.date_applied),
                ).fetchone()

            if existing:
                if existing["status"] in MANUAL_STATUSES:
                    # Never let automation downgrade a manually-set status —
                    # refresh metadata only.
                    conn.execute(
                        "UPDATE applications SET notes = COALESCE(?, notes), "
                        "blob_url = COALESCE(?, blob_url), last_updated = ? WHERE id = ?",
                        (item.notes, item.blob_url, now, existing["id"]),
                    )
                else:
                    conn.execute(
                        "UPDATE applications SET status = ?, notes = ?, blob_url = ?, "
                        "source = COALESCE(?, source), validation_status = ?, last_updated = ? WHERE id = ?",
                        (status, item.notes, item.blob_url, item.source, validation_status, now, existing["id"]),
                    )
            else:
                conn.execute(
                    "INSERT INTO applications (date_applied, company, role, url, status, notes, "
                    "blob_url, source, validation_status, last_updated) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (item.date_applied, company, role, url, status, item.notes,
                     item.blob_url, item.source, validation_status, now),
                )
            upserted += 1

    logger.info("applications ingested: upserted=%s skipped=%s", upserted, skipped)
    return {"status": "ok", "upserted": upserted, "skipped": skipped}
