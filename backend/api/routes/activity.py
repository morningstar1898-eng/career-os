from fastapi import APIRouter
from api.db import get_db

router = APIRouter()


@router.get("/recent")
def get_recent_activity():
    """Return the 10 most recent activities across runs, interviews, and metrics."""
    with get_db() as conn:
        # Agent runs
        runs = conn.execute(
            """SELECT id, finished_at AS ts, status FROM runs
               WHERE finished_at IS NOT NULL
               ORDER BY finished_at DESC LIMIT 10"""
        ).fetchall()

        # Interview sessions
        interviews = conn.execute(
            """SELECT id, started_at AS ts, category, score FROM interview_sessions
               ORDER BY started_at DESC LIMIT 10"""
        ).fetchall()

        # Daily metrics
        metrics = conn.execute(
            """SELECT id, date AS ts, jobs_applied FROM metrics
               ORDER BY date DESC LIMIT 10"""
        ).fetchall()

    activities = []

    for r in runs:
        row = dict(r)
        success = row["status"] == "success"
        activities.append({
            "type": "run",
            "status": "success" if success else "failure",
            "description": "Agent run completed" if success else "Agent run failed",
            "timestamp": row["ts"],
        })

    for i in interviews:
        row = dict(i)
        score_str = f" — score {row['score']}/10" if row["score"] is not None else ""
        activities.append({
            "type": "interview",
            "status": "interview",
            "description": f"Interview practiced: {row['category']}{score_str}",
            "timestamp": row["ts"],
        })

    for m in metrics:
        row = dict(m)
        activities.append({
            "type": "metrics",
            "status": "success",
            # metrics.jobs_applied is a legacy column name — it counts jobs FOUND
            "description": f"Daily metrics recorded — {row['jobs_applied']} jobs found",
            "timestamp": row["ts"],
        })

    # Sort by timestamp descending, take 10
    activities.sort(key=lambda a: a["timestamp"] or "", reverse=True)
    return activities[:10]
