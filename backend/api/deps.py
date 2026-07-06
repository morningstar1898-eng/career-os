"""
api/deps.py
Backend authentication. Every private route requires a bearer token:

    Authorization: Bearer <token>

Two kinds of token are accepted:
  1. The static API token from CAREER_OS_API_TOKEN (used by GitHub Actions
     and any server-to-server caller).
  2. A session token issued by POST /auth/login after the dashboard password
     check. Session tokens live in process memory and reset on redeploy —
     the frontend re-prompts for the password when that happens.

If CAREER_OS_API_TOKEN is not configured the API fails closed (500) rather
than serving private data unauthenticated.
"""
import hmac
from fastapi import Header, HTTPException

from api import config

# Session tokens issued by /auth/login (single-user dashboard; in-memory by design)
_session_tokens: set[str] = set()


def register_session_token(token: str) -> None:
    _session_tokens.add(token)


def is_valid_token(token: str) -> bool:
    expected = config.api_token()
    if expected and hmac.compare_digest(token, expected):
        return True
    return token in _session_tokens


def require_api_token(authorization: str | None = Header(default=None)):
    if not config.api_token():
        raise HTTPException(status_code=500, detail="API token not configured")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "", 1)

    if not is_valid_token(token):
        raise HTTPException(status_code=403, detail="Invalid token")
