"""
Career Profile onboarding + resume upload + LinkedIn paste + truthful
LinkedIn/resume recommendations. All rows are keyed to the authenticated user.
Resume and LinkedIn text are stored privately and never logged.
"""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.db import get_db
from api.saas import plans
from api.saas.deps import get_current_user
from api.saas.skills_data import CORE_DATA_AI_SKILLS

router = APIRouter()

LIST_FIELDS = [
    "target_roles", "target_locations", "industries", "companies_targeted",
    "companies_avoided", "current_skills", "desired_skills", "certifications",
    "portfolio_links",
]
TEXT_FIELDS = [
    "target_seniority", "remote_preference", "salary_target", "current_title",
    "education", "resume_summary", "linkedin_summary", "github_url",
    "job_search_urgency", "briefing_frequency", "gmail_connection_preference",
]


class ProfileUpdate(BaseModel):
    target_roles: list[str] | None = None
    target_seniority: str | None = None
    target_locations: list[str] | None = None
    remote_preference: str | None = None
    salary_target: str | None = None
    industries: list[str] | None = None
    companies_targeted: list[str] | None = None
    companies_avoided: list[str] | None = None
    current_title: str | None = None
    current_skills: list[str] | None = None
    desired_skills: list[str] | None = None
    education: str | None = None
    certifications: list[str] | None = None
    resume_summary: str | None = None
    linkedin_summary: str | None = None
    portfolio_links: list[str] | None = None
    github_url: str | None = None
    job_search_urgency: str | None = None
    briefing_frequency: str | None = None
    gmail_connection_preference: str | None = None


class ResumeUpload(BaseModel):
    name: str = "Resume"
    content: str


class LinkedInPaste(BaseModel):
    content: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_profile(row) -> dict:
    d = dict(row)
    for f in LIST_FIELDS:
        try:
            d[f] = json.loads(d[f]) if d[f] else []
        except (json.JSONDecodeError, TypeError):
            d[f] = []
    # Never return the raw pasted LinkedIn content in the profile summary view
    d["has_linkedin_content"] = bool(d.pop("linkedin_content", None))
    return d


def get_profile_row(user_id: int):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM career_profiles WHERE user_id = ?", (user_id,)
        ).fetchone()


@router.get("/profile")
def get_profile(user: dict = Depends(get_current_user)):
    row = get_profile_row(user["id"])
    if not row:
        return {"exists": False, "onboarding_complete": False}
    return {"exists": True, "onboarding_complete": True, **_row_to_profile(row)}


@router.put("/profile")
def upsert_profile(req: ProfileUpdate, user: dict = Depends(get_current_user)):
    """Onboarding + profile edits. Creates the Career Profile on first call."""
    data = req.model_dump(exclude_none=True)
    for f in LIST_FIELDS:
        if f in data:
            data[f] = json.dumps(data[f])

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM career_profiles WHERE user_id = ?", (user["id"],)
        ).fetchone()
        if existing:
            if data:
                sets = ", ".join(f"{k} = ?" for k in data)
                conn.execute(
                    f"UPDATE career_profiles SET {sets}, updated_at = ? WHERE user_id = ?",
                    (*data.values(), _now(), user["id"]),
                )
        else:
            cols = ", ".join(data.keys())
            marks = ", ".join("?" for _ in data)
            prefix = f"{cols}, " if data else ""
            conn.execute(
                f"INSERT INTO career_profiles ({prefix}user_id, created_at) VALUES ({marks}{', ' if data else ''}?, ?)",
                (*data.values(), user["id"], _now()),
            )
    return {"status": "ok"}


@router.put("/profile/linkedin")
def paste_linkedin(req: LinkedInPaste, user: dict = Depends(get_current_user)):
    content = req.content.strip()
    if not content:
        raise HTTPException(400, "LinkedIn content is empty")
    if len(content) > 100_000:
        raise HTTPException(413, "LinkedIn content too large")
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM career_profiles WHERE user_id = ?", (user["id"],)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE career_profiles SET linkedin_content = ?, updated_at = ? WHERE user_id = ?",
                (content, _now(), user["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO career_profiles (user_id, linkedin_content, created_at) VALUES (?, ?, ?)",
                (user["id"], content, _now()),
            )
    return {"status": "ok", "chars": len(content)}


@router.delete("/profile/linkedin")
def delete_linkedin(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        conn.execute(
            "UPDATE career_profiles SET linkedin_content = NULL, updated_at = ? WHERE user_id = ?",
            (_now(), user["id"]),
        )
    return {"status": "deleted"}


# ── Resumes ───────────────────────────────────────────────

@router.post("/resumes")
def upload_resume(req: ResumeUpload, user: dict = Depends(get_current_user)):
    plans.require_entitlement(user, "can_upload_resume")
    content = req.content.strip()
    if not content:
        raise HTTPException(400, "Resume content is empty")
    if len(content) > 200_000:
        raise HTTPException(413, "Resume too large")

    max_resumes = plans.limit_for(user, "max_resumes")
    with get_db() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM resumes WHERE user_id = ?", (user["id"],)
        ).fetchone()[0]
        if count >= max_resumes:
            raise HTTPException(403, f"Your plan allows up to {max_resumes} stored resume(s). Delete one first.")
        version = conn.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 FROM resumes WHERE user_id = ?", (user["id"],)
        ).fetchone()[0]
        cursor = conn.execute(
            "INSERT INTO resumes (user_id, name, content, version, created_at) VALUES (?, ?, ?, ?, ?)",
            (user["id"], req.name.strip()[:120] or "Resume", content, version, _now()),
        )
        resume_id = cursor.lastrowid
    return {"status": "ok", "resume_id": resume_id, "version": version}


@router.get("/resumes")
def list_resumes(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, version, length(content) AS chars, created_at "
            "FROM resumes WHERE user_id = ? ORDER BY id DESC",
            (user["id"],),
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/resumes/{resume_id}")
def get_resume(resume_id: int, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM resumes WHERE id = ? AND user_id = ?", (resume_id, user["id"]),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Resume not found")
        return dict(row)


@router.delete("/resumes/{resume_id}")
def delete_resume(resume_id: int, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM resumes WHERE id = ? AND user_id = ?", (resume_id, user["id"]),
        )
        if cursor.rowcount == 0:
            raise HTTPException(404, "Resume not found")
    return {"status": "deleted"}


# ── LinkedIn recommendations (truthful positioning only) ──

@router.get("/recommendations/linkedin")
def linkedin_recommendations(user: dict = Depends(get_current_user)):
    """Deterministic, truthful recommendations based on what the user has
    already told us — never invents experience."""
    row = get_profile_row(user["id"])
    if not row:
        raise HTTPException(400, "Complete your Career Profile first")
    profile = dict(row)
    content = (profile.get("linkedin_content") or "").lower()
    skills = json.loads(profile.get("current_skills") or "[]")
    targets = json.loads(profile.get("target_roles") or "[]")

    recs = []
    if not content:
        recs.append({
            "area": "profile_import",
            "recommendation": "Paste your LinkedIn profile content so recommendations can compare it against your target roles.",
        })
    else:
        # Skills the user says they have but that don't appear in their LinkedIn text
        missing = [s for s in skills if s and s.lower() not in content]
        if missing:
            recs.append({
                "area": "skills_section",
                "recommendation": f"You listed these skills in your profile but they don't appear in your LinkedIn content: {', '.join(missing[:8])}. Add the ones you genuinely use.",
            })
        if targets and not any(t.lower() in content for t in targets):
            recs.append({
                "area": "headline",
                "recommendation": f"Your headline/content doesn't mention your target role(s) ({', '.join(targets[:3])}). Recruiters search by title keywords — include the role you want, truthfully framed (e.g. 'transitioning to', 'building toward').",
            })
        core_missing = [s for s in CORE_DATA_AI_SKILLS[:12] if s.lower() in " ".join(skills).lower() and s.lower() not in content]
        if core_missing:
            recs.append({
                "area": "about_section",
                "recommendation": f"High-signal data/AI keywords you have but don't surface: {', '.join(core_missing[:6])}.",
            })
        if "http" not in content and not profile.get("portfolio_links"):
            recs.append({
                "area": "featured_links",
                "recommendation": "No portfolio or project links detected. Add your GitHub and 1-2 project links to the Featured section — proof beats claims.",
            })
    if profile.get("github_url") and content and "github" not in content:
        recs.append({
            "area": "featured_links",
            "recommendation": "Your GitHub isn't referenced on LinkedIn — add it to the Featured or Contact section.",
        })
    recs.append({
        "area": "disclaimer",
        "recommendation": "These are guidance based on your own stated skills and content — only add things that are true.",
    })
    return {"recommendations": recs}
