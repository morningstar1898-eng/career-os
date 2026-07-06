"""
Missing-skills engine, teaching moments, and portfolio project
recommendations for data/AI job seekers.

The gap analysis is deterministic (job requirements vs. the user's stated
skills + resume text). Lesson content is template-generated here; AI-generated
lessons plug into the same endpoint when an AI key is configured and
DISABLE_AI_RUNS is off. Language stays hedged: "possible gap", "likely
improvement area" — never unsupported claims.
"""
import json
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api import config
from api.db import get_db
from api.saas import plans, usage
from api.saas.deps import get_current_user
from api.saas.routes.profile import get_profile_row
from api.saas.skills_data import category_of

router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TeachingMomentRequest(BaseModel):
    skill: str


# ── Missing skills engine ─────────────────────────────────

@router.post("/skills/analyze")
def analyze_skill_gaps(user: dict = Depends(get_current_user)):
    """Compare all saved job requirements against the user's profile + latest
    resume; store ranked gaps."""
    plans.require_entitlement(user, "can_run_job_match")

    profile_row = get_profile_row(user["id"])
    if not profile_row:
        raise HTTPException(400, "Complete your Career Profile first")
    profile = dict(profile_row)
    user_skills = {s.lower() for s in json.loads(profile.get("current_skills") or "[]")}

    with get_db() as conn:
        resume = conn.execute(
            "SELECT content FROM resumes WHERE user_id = ? ORDER BY version DESC LIMIT 1",
            (user["id"],),
        ).fetchone()
        jobs = conn.execute(
            "SELECT id, company, role, required_skills FROM saas_jobs WHERE user_id = ?",
            (user["id"],),
        ).fetchall()
    resume_text = (resume["content"] if resume else "").lower()

    if not jobs:
        return {"gaps": [], "message": "Save some jobs first — gaps are computed from real postings."}

    gap_counter: Counter = Counter()
    evidence: dict[str, list] = {}
    for job in jobs:
        required = json.loads(job["required_skills"] or "[]")
        for skill in required:
            if skill.lower() not in user_skills and skill.lower() not in resume_text:
                gap_counter[skill] += 1
                evidence.setdefault(skill, []).append(
                    {"job_id": job["id"], "company": job["company"], "role": job["role"]}
                )

    now = _now()
    results = []
    with get_db() as conn:
        for skill, count in gap_counter.most_common(25):
            cat = category_of(skill)
            existing = conn.execute(
                "SELECT id FROM skill_gaps WHERE user_id = ? AND skill = ?",
                (user["id"], skill),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE skill_gaps SET jobs_count = ?, evidence = ?, updated_at = ? WHERE id = ?",
                    (count, json.dumps(evidence[skill][:10]), now, existing["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO skill_gaps (user_id, skill, category, evidence, jobs_count, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (user["id"], skill, cat, json.dumps(evidence[skill][:10]), count, now),
                )
            results.append({
                "skill": skill, "category": cat, "jobs_count": count,
                "note": f"Possible gap — appears in {count} of your saved postings and not in your profile or resume.",
            })

    return {"gaps": results, "jobs_analyzed": len(jobs),
            "disclaimer": "Based on keyword comparison of postings vs. your profile — review before acting."}


@router.get("/skills/gaps")
def list_skill_gaps(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM skill_gaps WHERE user_id = ? AND status != 'closed' "
            "ORDER BY jobs_count DESC, id",
            (user["id"],),
        ).fetchall()
        return [dict(r) for r in rows]


# ── Teaching moments ──────────────────────────────────────

def _template_teaching_moment(skill: str, jobs_evidence: list) -> dict:
    """Deterministic teaching moment. An AI-generated version can enrich this
    payload when a model key is configured — same schema either way."""
    return {
        "skill_gap": skill,
        "why_it_matters": f"{skill} appeared as a requirement in postings you saved — closing it directly improves your match rate.",
        "where_it_appeared_in_jobs": jobs_evidence[:5],
        "plain_english_explanation": f"A likely improvement area based on the job descriptions and your profile: {skill}.",
        "quick_lesson": f"Spend 45-60 minutes on {skill} fundamentals: what problem it solves, the core workflow, and one worked example in a data/AI context.",
        "practice_task": f"Build one small, runnable exercise using {skill} against a public dataset and commit it to GitHub.",
        "portfolio_task": f"Extend an existing portfolio project to demonstrate {skill}, and mention it in the README.",
        "quiz_question": f"In one paragraph: when would you choose {skill} over the closest alternative, and what's the main trade-off?",
        "recommended_resources": [
            {
                "title": f"Official {skill} documentation / getting-started guide",
                "provider": "official docs",
                "url": "",
                "free_or_paid": "free",
                "estimated_time": "1-2 hours",
                "skill_area": skill,
                "reason_recommended": "Primary sources age best; start here before courses.",
            }
        ],
        "resume_bullet_after_completion": f"(After you actually complete the practice task) 'Built <project> using {skill} to <outcome>' — only add once true.",
        "estimated_time": "1-3 hours",
    }


@router.post("/teaching-moments")
def create_teaching_moment(req: TeachingMomentRequest, user: dict = Depends(get_current_user)):
    plans.require_entitlement(user, "can_generate_lessons")
    if config.disable_ai_runs():
        # Kill switch only disables AI generation; the deterministic template still works.
        pass
    usage.check_and_increment(user, "lessons")

    skill = req.skill.strip()
    if not skill:
        raise HTTPException(400, "skill is required")

    with get_db() as conn:
        gap = conn.execute(
            "SELECT evidence FROM skill_gaps WHERE user_id = ? AND skill = ?",
            (user["id"], skill),
        ).fetchone()
    evidence = json.loads(gap["evidence"]) if gap and gap["evidence"] else []

    payload = _template_teaching_moment(skill, evidence)

    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO teaching_moments (user_id, skill_gap, payload, created_at) VALUES (?, ?, ?, ?)",
            (user["id"], skill, json.dumps(payload), _now()),
        )
    return {"teaching_moment_id": cursor.lastrowid, **payload}


@router.get("/teaching-moments")
def list_teaching_moments(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, skill_gap, payload, status, created_at FROM teaching_moments "
            "WHERE user_id = ? ORDER BY id DESC LIMIT 50",
            (user["id"],),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["payload"] = json.loads(d["payload"])
            except json.JSONDecodeError:
                pass
            out.append(d)
        return out


@router.patch("/teaching-moments/{tm_id}")
def update_teaching_moment(tm_id: int, body: dict, user: dict = Depends(get_current_user)):
    status = body.get("status", "")
    if status not in ("new", "completed", "dismissed"):
        raise HTTPException(400, "status must be new, completed, or dismissed")
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE teaching_moments SET status = ? WHERE id = ? AND user_id = ?",
            (status, tm_id, user["id"]),
        )
        if cursor.rowcount == 0:
            raise HTTPException(404, "Teaching moment not found")
    return {"status": "ok"}


# ── Portfolio project recommendations ─────────────────────

PORTFOLIO_TEMPLATES = {
    "data": {
        "project_title": "End-to-end analytics pipeline on a public dataset",
        "minimum_build": "Ingest a public dataset, clean/model it, and publish 3 charts answering one business question.",
        "stretch_build": "Add dbt models, tests, scheduled refresh, and a hosted dashboard.",
        "suggested_stack": ["Python", "SQL", "dbt", "GitHub Actions"],
    },
    "ai_ml": {
        "project_title": "RAG application over a domain document set",
        "minimum_build": "Chunk + embed a small document corpus, retrieve, and answer questions with citations.",
        "stretch_build": "Add evaluation, a vector database, and a simple web UI with feedback capture.",
        "suggested_stack": ["Python", "FastAPI", "Vector Databases", "LLM"],
    },
    "cloud": {
        "project_title": "Cloud data pipeline (bronze/silver/gold)",
        "minimum_build": "Land raw data in cloud storage, transform to typed tables, aggregate a mart.",
        "stretch_build": "Add orchestration, monitoring, cost notes, and IaC.",
        "suggested_stack": ["Azure", "Snowflake", "Airflow", "Terraform"],
    },
    "default": {
        "project_title": "Skill-focused mini project",
        "minimum_build": "One runnable repo demonstrating the skill against real data.",
        "stretch_build": "Add tests, CI, and a README that explains the business question.",
        "suggested_stack": ["Python", "SQL", "GitHub"],
    },
}


@router.get("/portfolio/recommendations")
def portfolio_recommendations(user: dict = Depends(get_current_user)):
    profile_row = get_profile_row(user["id"])
    targets = []
    if profile_row:
        targets = json.loads(dict(profile_row).get("target_roles") or "[]")
    with get_db() as conn:
        gaps = conn.execute(
            "SELECT skill, category, jobs_count FROM skill_gaps WHERE user_id = ? "
            "AND status != 'closed' ORDER BY jobs_count DESC LIMIT 5",
            (user["id"],),
        ).fetchall()

    recs = []
    for gap in gaps:
        template = PORTFOLIO_TEMPLATES.get(gap["category"], PORTFOLIO_TEMPLATES["default"])
        skill = gap["skill"]
        recs.append({
            **template,
            "target_role": targets[0] if targets else "Data/AI role",
            "skills_demonstrated": [skill] + [s for s in template["suggested_stack"] if s != skill][:3],
            "why_this_project_helps": f"'{skill}' appears in {gap['jobs_count']} of your saved postings — a project is the fastest credible proof.",
            "resume_bullets": [
                f"Built <project name> demonstrating {skill}: <measurable outcome> (add only after you build it)",
            ],
            "github_readme_outline": [
                "Problem & business question", "Data source", "Architecture / approach",
                f"How {skill} is used", "Results with screenshots", "How to run it", "What I'd do next",
            ],
            "demo_script": f"60-second walkthrough: the question → the {skill} piece → the result → what you'd do at scale.",
        })
    return {"recommendations": recs,
            "note": "Run POST /v1/skills/analyze first if this list is empty."}
