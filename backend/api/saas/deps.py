"""
api/saas/deps.py
Request dependencies for the multi-user SaaS routes: resolve the authenticated
user from a session JWT, and enforce the admin role server-side.
"""
from fastapi import Header, HTTPException

from api.db import get_db
from api.saas.security import decode_session_token


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    return authorization.replace("Bearer ", "", 1)


def get_user_by_id(user_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    payload = decode_session_token(_bearer(authorization))
    try:
        user_id = int(payload.get("sub", ""))
    except ValueError:
        raise HTTPException(401, "Invalid session token")
    user = get_user_by_id(user_id)
    if not user or user.get("status") == "deleted":
        raise HTTPException(401, "Account not found")
    if user.get("status") == "suspended":
        raise HTTPException(403, "Account suspended")
    return user


def require_admin(authorization: str | None = Header(default=None)) -> dict:
    """Admin role is checked against the DATABASE row, never the token alone
    or anything the frontend sends."""
    user = get_current_user(authorization)
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    return user
