from datetime import datetime
from fastapi import APIRouter, HTTPException
from api.db import get_db
from api.models import BriefingResponse

router = APIRouter()


@router.get("/today", response_model=BriefingResponse)
def get_today_briefing():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with get_db() as conn:
        row = conn.execute("SELECT * FROM briefings WHERE date = ?", (today,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No briefing for today yet")
        return BriefingResponse(**dict(row))


@router.get("/history")
def get_briefing_history(limit: int = 7):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM briefings ORDER BY date DESC LIMIT ?", (limit,)
        ).fetchall()
        return [BriefingResponse(**dict(r)) for r in rows]
