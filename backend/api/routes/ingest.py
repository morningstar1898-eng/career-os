import os
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from api.db import get_db

router = APIRouter()


class IngestRequest(BaseModel):
    secret: str
    crew_output: str
    jobs_applied: int = 0
    skills_gap_count: int = 0
    portfolio_items: int = 0


class ApplicationItem(BaseModel):
    date_applied: str
    company: str
    role: str
    url: Optional[str] = None
    status: str = "Applied"
    notes: Optional[str] = None
    blob_url: Optional[str] = None


class ApplicationsIngestRequest(BaseModel):
    secret: str
    applications: List[ApplicationItem]


@router.post("/crew-result")
def ingest_crew_result(req: IngestRequest):
    expected = os.getenv("INGEST_SECRET", "")
    if not expected or req.secret != expected:
        raise HTTPException(403, "Invalid secret")

    today = datetime.utcnow().strftime("%Y-%m-%d")
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO runs (started_at, finished_at, status, trigger) VALUES (?, ?, 'success', 'cron')",
            (now, now),
        )
        run_id = cursor.lastrowid

        content = json.dumps({"raw_output": req.crew_output})
        conn.execute(
            "INSERT OR REPLACE INTO briefings (run_id, date, content_json) VALUES (?, ?, ?)",
            (run_id, today, content),
        )

        conn.execute(
            "INSERT INTO metrics (date, jobs_applied, skills_gap_count, interview_score, portfolio_items) VALUES (?, ?, ?, 0, ?)",
            (today, req.jobs_applied, req.skills_gap_count, req.portfolio_items),
        )

    return {"status": "ok", "run_id": run_id, "date": today}


@router.post("/applications")
def ingest_applications(req: ApplicationsIngestRequest):
    expected = os.getenv("INGEST_SECRET", "")
    if not expected or req.secret != expected:
        raise HTTPException(403, "Invalid secret")
    if not req.applications:
        return {"status": "ok", "upserted": 0}

    now = datetime.utcnow().isoformat()
    upserted = 0
    with get_db() as conn:
        for app in req.applications:
            existing = conn.execute(
                "SELECT id FROM applications WHERE company = ? AND role = ? AND date_applied = ?",
                (app.company, app.role, app.date_applied)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE applications SET status = ?, notes = ?, blob_url = ?, last_updated = ? WHERE id = ?",
                    (app.status, app.notes, app.blob_url, now, existing["id"])
                )
            else:
                conn.execute(
                    "INSERT INTO applications (date_applied, company, role, url, status, notes, blob_url, last_updated) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (app.date_applied, app.company, app.role, app.url, app.status, app.notes, app.blob_url, now)
                )
            upserted += 1

    return {"status": "ok", "upserted": upserted}
