import os
import hashlib
import secrets
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

_tokens: set[str] = set()


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
    if req.password != expected:
        raise HTTPException(401, "Invalid password")
    token = secrets.token_hex(32)
    _tokens.add(token)
    return LoginResponse(token=token)


@router.post("/verify", response_model=VerifyResponse)
def verify_token(req: dict):
    token = req.get("token", "")
    if token in _tokens:
        return VerifyResponse(valid=True)
    return VerifyResponse(valid=False)
