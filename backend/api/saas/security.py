"""
api/saas/security.py
Password hashing and user session tokens for the multi-user SaaS layer.

- Passwords: hashlib.scrypt (stdlib, memory-hard KDF) with a per-user random
  salt, verified with constant-time comparison. Format:
      scrypt$<n>$<r>$<p>$<salt_hex>$<hash_hex>
- Sessions: signed JWTs (PyJWT, HS256) with expiry. The signing secret comes
  from AUTH_SECRET — SaaS auth routes refuse to run without it (fail closed).
"""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException

from api import config

# scrypt parameters (OWASP-reasonable for interactive login)
_N, _R, _P = 2 ** 14, 8, 1
TOKEN_TTL_DAYS = 7


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_hex, hash_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode("utf-8"), salt=bytes.fromhex(salt_hex),
            n=int(n), r=int(r), p=int(p), dklen=32,
        )
        return hmac.compare_digest(digest.hex(), hash_hex)
    except Exception:
        return False


def _secret() -> str:
    secret = config.auth_secret()
    if not secret:
        raise HTTPException(500, "AUTH_SECRET not configured — SaaS auth is disabled")
    return secret


def create_session_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=TOKEN_TTL_DAYS)).timestamp()),
        "typ": "user",
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")


def decode_session_token(token: str) -> dict:
    """Returns the payload or raises 401."""
    try:
        return jwt.decode(token, _secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Session expired — please log in again")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid session token")
