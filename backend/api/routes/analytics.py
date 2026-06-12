from fastapi import APIRouter
from api.db import get_db
from api.models import MetricsResponse

router = APIRouter()


@router.get("/metrics")
def get_metrics(days: int = 30):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM metrics ORDER BY date DESC LIMIT ?", (days,)
        ).fetchall()
        return [MetricsResponse(**dict(r)) for r in rows]


@router.get("/summary")
def get_summary():
    with get_db() as conn:
        total_jobs = conn.execute("SELECT COALESCE(SUM(jobs_applied), 0) FROM metrics").fetchone()[0]
        total_runs = conn.execute("SELECT COUNT(*) FROM runs WHERE status = 'success'").fetchone()[0]
        avg_score = conn.execute("SELECT COALESCE(AVG(score), 0) FROM interview_sessions WHERE score IS NOT NULL").fetchone()[0]
        return {
            "total_jobs_applied": total_jobs,
            "total_successful_runs": total_runs,
            "avg_interview_score": round(avg_score, 1),
            "days_active": conn.execute("SELECT COUNT(DISTINCT date) FROM metrics").fetchone()[0],
        }
