import os
import hmac
import secrets
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.deps import register_session_token, is_valid_token

router = APIRouter()


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    token: str


class VerifyResponse(BaseModel):
    valid: bool


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    expected = os.getenv("CAREER_OS_PASSWORD", "")
    if not expected:
        raise HTTPException(500, "No password configured")
    if not hmac.compare_digest(req.password, expected):
        raise HTTPException(401, "Invalid password")
    token = secrets.token_hex(32)
    register_session_token(token)
    return LoginResponse(token=token)


@router.post("/verify", response_model=VerifyResponse)
def verify_token(req: dict):
    token = req.get("token", "")
    return VerifyResponse(valid=bool(token) and is_valid_token(token))
