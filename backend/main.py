"""
main.py
Entry point. Run this manually or via GitHub Actions cron.
Usage: python main.py
"""
import os, sys, time
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Make ALL json parsing tolerant of a leading UTF-8 BOM. Tool-call inputs from
# the model sometimes arrive with a BOM that crashes CrewAI's own argument
# parsing *before* a tool runs — which was silently breaking every Google
# Sheets application log. Patch globally so CrewAI internals are covered too.
import json as _json
_orig_json_loads = _json.loads
def _bom_safe_loads(s, *args, **kwargs):
    if isinstance(s, (bytes, bytearray)):
        s = s.decode("utf-8-sig")
    elif isinstance(s, str):
        s = s.lstrip("﻿")
    return _orig_json_loads(s, *args, **kwargs)
_json.loads = _bom_safe_loads

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from crewai import Crew, Process
from agents.crew_agents import build_agents
from agents.crew_tasks import build_tasks

def run_career_os():
    start = time.time()
    print(f"\n{'='*60}")
    print(f"  Career OS — {datetime.now().strftime('%A %B %d, %Y at %I:%M %p')}")
    print(f"{'='*60}\n")

    # Validate required env vars before spending API tokens
    required = [
        "ANTHROPIC_API_KEY", "SERPER_API_KEY",
        "NOTION_API_KEY", "NOTION_DATABASE_ID",
        "GOOGLE_CREDENTIALS_JSON", "GOOGLE_SHEET_ID",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"❌ Missing env vars: {', '.join(missing)}")
        print("   Copy .env.template to .env and fill in your keys.")
        sys.exit(1)

    os.makedirs("outputs", exist_ok=True)

    print("🤖 Building agent crew...")
    agents = build_agents()

    print("📋 Defining today's tasks...")
    tasks = build_tasks(agents)

    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,   # tasks run in order, each feeds the next
        verbose=True,
        memory=False,                  # stateless — GitHub Actions restarts clean
        max_rpm=20,                    # stay within Claude API rate limits
    )

    print("\n🚀 Launching crew...\n")
    result = crew.kickoff()

    elapsed = round((time.time() - start) / 60, 1)
    print(f"\n{'='*60}")
    print(f"  ✅ Done in {elapsed} minutes")
    print(f"  Check your Notion for today's briefing.")
    print(f"{'='*60}\n")

    return result

if __name__ == "__main__":
    run_career_os()
