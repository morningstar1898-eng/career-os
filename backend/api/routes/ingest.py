import os
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from api.db import get_db

router = APIRouter()


class IngestRequest(BaseModel):
    secret: str
    crew_output: str
    jobs_applied: int = 0
    skills_gap_count: int = 0
    portfolio_items: int = 0


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
