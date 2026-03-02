"""
Authentication API endpoints.

Provides signup, login, token refresh, and user-info routes.
JWTs are signed with the same ADMIN_PRIVATE_KEY used elsewhere.
"""

from __future__ import annotations

import os
import time
from typing import Dict, Optional

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ai_receptionist.core.database import get_db
from ai_receptionist.models.user import User
from ai_receptionist.models.tenant import Tenant
from ai_receptionist.services.auth.password import hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Pydantic request / response schemas
# ---------------------------------------------------------------------------


class SignupRequest(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    tenant_name: Optional[str] = None   # defaults to capitalised username


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    tenant_id: Optional[str] = None
    plan: Optional[str] = None

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    user: UserOut
    token: str


# ---------------------------------------------------------------------------
# JWT helpers – reuses ADMIN_PRIVATE_KEY for signing
# ---------------------------------------------------------------------------

_TOKEN_TTL = 60 * 60 * 24  # 24 h


def _jwt_key() -> str:
    key = os.environ.get("ADMIN_PRIVATE_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="JWT signing key not configured")
    return key


def _make_user_token(user_id: int, tenant_id: str) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "tenant_id": tenant_id,
        "iat": now,
        "exp": now + _TOKEN_TTL,
    }
    return jwt.encode(payload, _jwt_key(), algorithm="HS256")


def _decode_user_token(token: str) -> Dict:
    try:
        return jwt.decode(token, _jwt_key(), algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="invalid or expired token")


# ---------------------------------------------------------------------------
# Dependency: current user from Bearer token
# ---------------------------------------------------------------------------


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    payload = _decode_user_token(authorization.split(" ", 1)[1])
    user = db.query(User).get(int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="user not found or inactive")
    return user


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/signup", response_model=AuthResponse)
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=409, detail="username already taken")

    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
    )
    db.add(user)
    db.flush()  # get user.id

    tenant_id = body.username.lower()
    tenant_name = body.tenant_name or body.username.capitalize()
    tenant = Tenant(
        id=tenant_id,
        name=tenant_name,
        owner_user_id=user.id,
    )
    db.add(tenant)
    db.commit()
    db.refresh(user)

    token = _make_user_token(user.id, tenant_id)
    return AuthResponse(
        user=UserOut(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            tenant_id=tenant_id,
            plan=tenant.plan,
        ),
        token=token,
    )


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")

    tenant = db.query(Tenant).filter(Tenant.owner_user_id == user.id).first()
    tenant_id = tenant.id if tenant else "default"
    plan = tenant.plan if tenant else "starter"

    token = _make_user_token(user.id, tenant_id)
    return AuthResponse(
        user=UserOut(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            tenant_id=tenant_id,
            plan=plan,
        ),
        token=token,
    )


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.owner_user_id == user.id).first()
    return UserOut(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        tenant_id=tenant.id if tenant else None,
        plan=tenant.plan if tenant else None,
    )


@router.post("/logout")
def logout():
    """Client discards token; nothing to do server-side for stateless JWTs."""
    return {"ok": True}
