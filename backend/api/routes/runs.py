import asyncio
import threading
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, HTTPException
from api.db import get_db
from api.models import RunResponse, RunTriggerRequest
from api.ws import broadcast

router = APIRouter()

_active_loop = None


def _run_crew(run_id: int):
    import sys
    import os
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from agents.crew_agents import build_agents
    from agents.crew_tasks import build_tasks
    from crewai import Crew, Process
    import json

    class StreamCapture:
        def __init__(self, original, loop):
            self.original = original
            self.loop = loop
            self.encoding = getattr(original, "encoding", "utf-8")

        def write(self, text):
            self.original.write(text)
            if text.strip() and self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(broadcast(text.rstrip()), self.loop)
            return len(text)

        def flush(self):
            self.original.flush()

        def fileno(self):
            return self.original.fileno()

    loop = _active_loop
    capture = StreamCapture(sys.stdout, loop)
    old_stdout = sys.stdout
    sys.stdout = capture

    try:
        os.makedirs("outputs", exist_ok=True)
        agents = build_agents()
        tasks = build_tasks(agents)
        crew = Crew(
            agents=list(agents.values()),
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
            memory=False,
            max_rpm=20,
        )
        result = crew.kickoff()

        with get_db() as conn:
            conn.execute(
                "UPDATE runs SET finished_at = ?, status = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), "success", run_id),
            )
            today = datetime.utcnow().strftime("%Y-%m-%d")
            content = json.dumps({"raw_output": str(result)})
            conn.execute(
                "INSERT OR REPLACE INTO briefings (run_id, date, content_json) VALUES (?, ?, ?)",
                (run_id, today, content),
            )
            conn.execute(
                "INSERT INTO metrics (date, jobs_applied, skills_gap_count, portfolio_items) VALUES (?, 5, 10, 3)",
                (today,),
            )
    except Exception as e:
        with get_db() as conn:
            conn.execute(
                "UPDATE runs SET finished_at = ?, status = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), f"failed: {str(e)[:200]}", run_id),
            )
    finally:
        sys.stdout = old_stdout


@router.post("/trigger", response_model=RunResponse)
def trigger_run(req: RunTriggerRequest, background_tasks: BackgroundTasks):
    global _active_loop
    try:
        _active_loop = asyncio.get_running_loop()
    except RuntimeError:
        _active_loop = None

    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO runs (started_at, status, trigger) VALUES (?, 'running', ?)",
            (datetime.utcnow().isoformat(), req.trigger),
        )
        run_id = cursor.lastrowid

    background_tasks.add_task(_run_crew_in_thread, run_id)

    with get_db() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return RunResponse(**dict(row))


def _run_crew_in_thread(run_id: int):
    thread = threading.Thread(target=_run_crew, args=(run_id,), daemon=True)
    thread.start()


@router.get("/status/{run_id}", response_model=RunResponse)
def get_run_status(run_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Run not found")
        return RunResponse(**dict(row))


@router.get("/latest", response_model=RunResponse)
def get_latest_run():
    with get_db() as conn:
        row = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No runs yet")
        return RunResponse(**dict(row))
