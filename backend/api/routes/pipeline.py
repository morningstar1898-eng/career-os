from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from api.db import get_db

router = APIRouter()

# Automation may only create Found / Saved / Drafted / Ready to Apply
# (enforced in /ingest). "Applied" and beyond are set here — by a manual user
# action on the authenticated dashboard — or by a confirmed Gmail/application
# event, because only the user actually submits applications.
VALID_STATUSES = [
    "Found", "Saved", "Drafted", "Ready to Apply",
    "Applied", "Confirmation Received", "Recruiter Screen", "Assessment",
    "Phone Screen", "Interview", "Offer",
    "Rejected", "Ghosted", "Withdrawn",
]


class StatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class ApplicationResponse(BaseModel):
    id: int
    date_applied: str
    company: str
    role: str
    url: Optional[str] = None
    status: str
    notes: Optional[str] = None
    blob_url: Optional[str] = None
    last_updated: Optional[str] = None
    days_since_applied: Optional[int] = None
    source: Optional[str] = None
    validation_status: Optional[str] = None


def _enrich(row: dict) -> dict:
    try:
        applied = datetime.strptime(row["date_applied"], "%Y-%m-%d")
        row["days_since_applied"] = (datetime.utcnow() - applied).days
    except Exception:
        row["days_since_applied"] = None
    return row


@router.get("/", response_model=list[ApplicationResponse])
def get_pipeline():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM applications ORDER BY date_applied DESC"
        ).fetchall()
        return [ApplicationResponse(**_enrich(dict(r))) for r in rows]


@router.get("/summary")
def get_pipeline_summary():
    with get_db() as conn:
        rows = conn.execute("SELECT status, COUNT(*) as count FROM applications GROUP BY status").fetchall()
        counts = {r["status"]: r["count"] for r in rows}
        total = sum(counts.values())
        in_progress = counts.get("Phone Screen", 0) + counts.get("Interview", 0)
        return {
            "total": total,
            "by_status": counts,
            "in_progress": in_progress,
            "offer_rate": round(counts.get("Offer", 0) / total * 100, 1) if total else 0,
        }


@router.get("/followup", response_model=list[ApplicationResponse])
def get_followup_needed(days: int = 7):
    """Applications still at 'Applied' status after N days with no update."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM applications WHERE status = 'Applied' AND date_applied <= ? ORDER BY date_applied ASC",
            (cutoff,)
        ).fetchall()
        return [ApplicationResponse(**_enrich(dict(r))) for r in rows]


@router.patch("/{app_id}/status")
def update_status(app_id: int, req: StatusUpdate):
    if req.status not in VALID_STATUSES:
        raise HTTPException(400, f"Status must be one of: {VALID_STATUSES}")
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        row = conn.execute("SELECT id FROM applications WHERE id = ?", (app_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Application not found")
        if req.notes is not None:
            conn.execute(
                "UPDATE applications SET status = ?, notes = ?, last_updated = ? WHERE id = ?",
                (req.status, req.notes, now, app_id)
            )
        else:
            conn.execute(
                "UPDATE applications SET status = ?, last_updated = ? WHERE id = ?",
                (req.status, now, app_id)
            )
    return {"status": "ok", "app_id": app_id, "new_status": req.status}
