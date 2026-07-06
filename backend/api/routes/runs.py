import asyncio
import logging
import threading
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, HTTPException
from api import config
from api.db import get_db
from api.models import RunResponse, RunTriggerRequest
from api.ws import broadcast

router = APIRouter()
logger = logging.getLogger("career_os.runs")

_active_loop = None


def _set_stage(run_id: int, stage: str):
    with get_db() as conn:
        conn.execute("UPDATE runs SET stage = ? WHERE id = ?", (stage, run_id))
    logger.info("run %s stage=%s", run_id, stage)


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
        _set_stage(run_id, "building_agents")
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
        _set_stage(run_id, "crew_running")
        result = crew.kickoff()

        _set_stage(run_id, "saving_results")
        with get_db() as conn:
            conn.execute(
                "UPDATE runs SET finished_at = ?, status = ?, stage = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), "success", "done", run_id),
            )
            today = datetime.utcnow().strftime("%Y-%m-%d")
            content = json.dumps({"raw_output": str(result)})
            conn.execute(
                "INSERT OR REPLACE INTO briefings (run_id, date, content_json) VALUES (?, ?, ?)",
                (run_id, today, content),
            )
        logger.info("run %s finished: success", run_id)
    except Exception as e:
        logger.exception("run %s failed", run_id)
        with get_db() as conn:
            conn.execute(
                "UPDATE runs SET finished_at = ?, status = ?, error_message = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), "failed", str(e)[:500], run_id),
            )
    finally:
        sys.stdout = old_stdout


@router.post("/trigger", response_model=RunResponse)
def trigger_run(req: RunTriggerRequest, background_tasks: BackgroundTasks):
    # Manual runs spend real API budget — they must be explicitly enabled.
    if not config.allow_manual_runs():
        raise HTTPException(
            status_code=403,
            detail="Manual runs are disabled. Set ALLOW_MANUAL_RUNS=true to enable.",
        )

    global _active_loop
    try:
        _active_loop = asyncio.get_running_loop()
    except RuntimeError:
        _active_loop = None

    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO runs (started_at, status, trigger, stage) VALUES (?, 'running', ?, 'started')",
            (datetime.utcnow().isoformat(), req.trigger),
        )
        run_id = cursor.lastrowid

    background_tasks.add_task(_run_crew_in_thread, run_id)

    with get_db() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return RunResponse(**_run_fields(row))


def _run_crew_in_thread(run_id: int):
    thread = threading.Thread(target=_run_crew, args=(run_id,), daemon=True)
    thread.start()


def _run_fields(row) -> dict:
    d = dict(row)
    return {k: d.get(k) for k in ("id", "started_at", "finished_at", "status", "trigger", "stage", "error_message")}


@router.get("/status/{run_id}", response_model=RunResponse)
def get_run_status(run_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Run not found")
        return RunResponse(**_run_fields(row))


@router.get("/latest", response_model=RunResponse)
def get_latest_run():
    with get_db() as conn:
        row = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No runs yet")
        return RunResponse(**_run_fields(row))
