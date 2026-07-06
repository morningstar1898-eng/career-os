# Career OS — Recruiter Demo Checklist

## Run locally (private mode)

```bash
# Backend
cd backend && python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
# .env at repo root: set CAREER_OS_API_TOKEN, CAREER_OS_PASSWORD at minimum
uvicorn api.main:app --reload

# Frontend (second terminal)
cd frontend && npm install && npm run dev
```

Open http://localhost:3000, log in with your `CAREER_OS_PASSWORD`.

## Run in demo mode (safe to show anyone)

```bash
# backend .env
PUBLIC_DEMO_MODE=true          # serves a SEPARATE demo database — real data never loads
CAREER_OS_API_TOKEN=demo-token
CAREER_OS_PASSWORD=demo

# frontend
NEXT_PUBLIC_DEMO_MODE=true
```

Start both, log in, click **Load Demo Data** on the landing page. Everything shown is fictitious (Lakeside Health Analytics, Nimbus Data Co., …).

## 3-minute walkthrough

1. **Landing page (30s)** — the honest pitch: human-in-the-loop, agents draft, you decide. Point at the architecture diagram.
2. **Dashboard (45s)** — daily briefing sections, metrics over time, activity feed. "Every weekday a GitHub Actions cron runs the crew and this populates itself."
3. **Pipeline Kanban (45s)** — the truthfulness story sells well: "Agents can only create Found/Drafted/Ready to Apply. The API literally rejects automation setting Applied — only I can, because only I actually apply."
4. **Interview practice (30s)** — start a question, show the AI scoring + model answer.
5. **Close (30s)** — security model (bearer auth, demo isolation), CI, and what you'd change at scale (Postgres, real user accounts).

## What NOT to show publicly

- The real (non-demo) instance — it names companies being applied to
- The Google Sheet tracker, Notion briefings, or real briefing emails
- `.env`, GitHub secrets, Azure portal
- Anything identifying the current employer relationship to the job search

## How to explain it in interviews

- *"I built a multi-agent AI system I actually use every day"* — real user, real workflow, real constraints (agent refusals, token budgets, GitHub cron unreliability) and how each was solved.
- *"Automation drafts, the human decides"* — show that the boundary is enforced in the API, not just in prompt text.
- *"I audited and hardened it"* — bearer auth, fail-closed design, demo/production data isolation, secret-free repo, CI.
- Trade-offs you can defend: SQLite over Postgres (single user), in-memory session tokens (redeploy = re-login), localStorage tokens (private single-user dashboard).

## Known limitations (say them before they ask)

- Single-user; no accounts or roles
- Job validation = canonical URL + dedupe, not live re-fetch of each posting
- No monitoring/alerting beyond run records and Actions logs
- SQLite on a persistent mount, not a managed database

## Next planned improvements

Postgres option · live posting re-validation (`expired` status) · stage-level run telemetry in the monitor · one-click "mark Applied" browser helper at submit time
