"""
SaaS account routes: signup (starts the 3-day no-card trial), login, session
info, data export, and account deletion. Passwords are scrypt-hashed; sessions
are signed JWTs. Signups can be paused with DISABLE_NEW_SIGNUPS.
"""
import json
import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api import config
from api.db import get_db
from api.saas import plans, usage
from api.saas.deps import get_current_user
from api.saas.security import hash_password, verify_password, create_session_token

router = APIRouter()
logger = logging.getLogger("career_os.saas.auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Tables wiped on account deletion / included in export (all keyed by user_id)
USER_TABLES = [
    "career_profiles", "resumes", "saas_jobs", "saas_applications",
    "application_events", "skill_gaps", "teaching_moments",
    "gmail_connections", "email_events", "usage_records", "feedback",
    "assist_audit_log",
]


class SignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class SessionResponse(BaseModel):
    token: str
    user_id: int
    email: str
    role: str
    plan: str
    trial_ends_at: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session(user: dict) -> SessionResponse:
    return SessionResponse(
        token=create_session_token(user["id"], user["role"]),
        user_id=user["id"],
        email=user["email"],
        role=user["role"],
        plan=plans.effective_plan(user),
        trial_ends_at=user.get("trial_ends_at"),
    )


@router.post("/auth/signup", response_model=SessionResponse)
def signup(req: SignupRequest):
    if config.disable_new_signups():
        raise HTTPException(503, "New signups are temporarily disabled.")
    email = req.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "Invalid email address")
    if len(req.password) < 10:
        raise HTTPException(400, "Password must be at least 10 characters")

    role = "admin" if email and email == config.admin_email() else "user"
    trial = plans.new_trial_fields()

    with get_db() as conn:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            raise HTTPException(409, "An account with this email already exists")
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash, role, status, plan, trial_started_at, "
            "trial_ends_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (email, hash_password(req.password), role, trial["status"], trial["plan"],
             trial["trial_started_at"], trial["trial_ends_at"], _now(), _now()),
        )
        user = dict(conn.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone())

    logger.info("signup: user_id=%s role=%s trial_ends=%s", user["id"], role, trial["trial_ends_at"])
    return _session(user)


@router.post("/auth/login", response_model=SessionResponse)
def login(req: LoginRequest):
    email = req.email.strip().lower()
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    # Uniform error whether the account exists or not.
    if not row or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    user = dict(row)
    if user["status"] == "deleted":
        raise HTTPException(401, "Invalid email or password")
    if user["status"] == "suspended":
        raise HTTPException(403, "Account suspended")
    with get_db() as conn:
        conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (_now(), user["id"]))
    logger.info("login: user_id=%s", user["id"])
    return _session(user)


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {
        "user_id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "status": user["status"],
        "plan": plans.effective_plan(user),
        "stored_plan": user["plan"],
        "trial_started_at": user["trial_started_at"],
        "trial_ends_at": user["trial_ends_at"],
        "trial_active": plans.trial_active(user),
        "subscription_status": user["subscription_status"],
        "entitlements": plans.entitlements(user),
        "usage_today": usage.usage_summary(user["id"]),
        "app_name": config.public_app_name(),
    }


@router.get("/me/export")
def export_my_data(user: dict = Depends(get_current_user)):
    """Full export of everything stored for this user (data portability)."""
    export: dict = {"user": {k: v for k, v in user.items() if k != "password_hash"}}
    with get_db() as conn:
        for table in USER_TABLES:
            rows = conn.execute(f"SELECT * FROM {table} WHERE user_id = ?", (user["id"],)).fetchall()
            export[table] = [dict(r) for r in rows]
    return export


@router.delete("/me")
def delete_my_account(user: dict = Depends(get_current_user)):
    """Hard-delete all user data; the user row is anonymized and tombstoned."""
    with get_db() as conn:
        for table in USER_TABLES:
            conn.execute(f"DELETE FROM {table} WHERE user_id = ?", (user["id"],))
        conn.execute(
            "UPDATE users SET email = ?, password_hash = 'deleted', status = 'deleted', "
            "stripe_customer_id = NULL, stripe_subscription_id = NULL, updated_at = ? WHERE id = ?",
            (f"deleted-{user['id']}@deleted.invalid", _now(), user["id"]),
        )
    logger.info("account deleted: user_id=%s", user["id"])
    return {"status": "deleted"}
