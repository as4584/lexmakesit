"""
Authentication API endpoints.

Flow:
  1. POST /api/auth/signup   → creates unverified user, sends verification email
  2. GET  /api/auth/verify-email?token=  → marks email verified, prompts password setup
  3. POST /api/auth/set-password         → sets password after email verification
  4. POST /api/auth/login                → email + password, blocks unverified accounts
  5. POST /api/auth/forgot-password      → sends password reset email
  6. POST /api/auth/reset-password       → sets new password with reset token
  7. GET  /api/auth/me                   → current user info
  8. POST /api/auth/logout               → stateless, client discards token
"""

from __future__ import annotations

import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, Response, Cookie
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ai_receptionist.core.database import get_db
from ai_receptionist.models.user import User
from ai_receptionist.models.tenant import Tenant
from ai_receptionist.services.auth.password import hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    email: str
    full_name: Optional[str] = None


class SetPasswordRequest(BaseModel):
    token: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class UserOut(BaseModel):
    id: int
    email: Optional[str]
    full_name: Optional[str]
    tenant_id: Optional[str] = None
    plan: Optional[str] = None
    email_verified: bool = False

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    user: UserOut
    token: str


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

_TOKEN_TTL = 60 * 60 * 24 * 7  # 7 days
_COOKIE_NAME = "auth_token"


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


def _set_auth_cookie(response: Response, token: str) -> None:
    """Set the auth JWT as an HttpOnly cookie."""
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        max_age=_TOKEN_TTL,
        httponly=True,
        secure=True,   # HTTPS only in production
        samesite="lax",
        path="/",
    )


# ---------------------------------------------------------------------------
# Dependency: current user from cookie OR Bearer token
# ---------------------------------------------------------------------------

def get_current_user(
    authorization: Optional[str] = Header(default=None),
    auth_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    # Prefer cookie; fall back to Bearer header
    token: Optional[str] = None
    if auth_token:
        token = auth_token
    elif authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = _decode_user_token(token)
    user = db.query(User).get(int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="user not found or inactive")
    return user


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/signup")
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    """
    Register with email. Sends a verification email with a link to set password.
    """
    from ai_receptionist.services.email.sendgrid_service import send_verification_email

    email = body.email.lower().strip()

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    token = secrets.token_urlsafe(32)

    # Use email prefix as username (unique within our system)
    username = email.split("@")[0]
    base_username = username
    counter = 1
    while db.query(User).filter(User.username == username).first():
        username = f"{base_username}{counter}"
        counter += 1

    user = User(
        username=username,
        email=email,
        password_hash="",  # set after email verification
        full_name=body.full_name,
        email_verified=False,
        email_verification_token=token,
    )
    db.add(user)
    db.flush()

    tenant_id = username.lower()
    tenant = Tenant(
        id=tenant_id,
        name=body.full_name or username.capitalize(),
        owner_user_id=user.id,
    )
    db.add(tenant)
    db.commit()

    send_verification_email(email, token)

    return {"ok": True, "message": "Check your email to verify your account and set your password."}


@router.post("/set-password")
def set_password(body: SetPasswordRequest, response: Response, db: Session = Depends(get_db)):
    """
    Called after clicking the verification link. Sets the password and marks email verified.
    """
    if len(body.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters.")

    user = db.query(User).filter(User.email_verification_token == body.token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link.")

    user.password_hash = hash_password(body.password)
    user.email_verified = True
    user.email_verification_token = None
    db.commit()

    tenant = db.query(Tenant).filter(Tenant.owner_user_id == user.id).first()
    tenant_id = tenant.id if tenant else "default"
    jwt_token = _make_user_token(user.id, tenant_id)
    _set_auth_cookie(response, jwt_token)

    return AuthResponse(
        user=UserOut(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            tenant_id=tenant_id,
            plan=tenant.plan if tenant else "starter",
            email_verified=True,
        ),
        token=jwt_token,
    )


@router.get("/verify-email")
def verify_email_get(token: str, db: Session = Depends(get_db)):
    """
    Called when user clicks the link in the verification email.
    Returns the token so the frontend can show the set-password form.
    """
    user = db.query(User).filter(User.email_verification_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link.")
    return {"ok": True, "token": token, "email": user.email}


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    email = body.email.lower().strip()

    # Try email first, fall back to username (for legacy accounts)
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = db.query(User).filter(User.username == email).first()

    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not user.email_verified:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email first. Check your inbox for a verification link."
        )

    tenant = db.query(Tenant).filter(Tenant.owner_user_id == user.id).first()
    tenant_id = tenant.id if tenant else "default"
    plan = tenant.plan if tenant else "starter"

    jwt_token = _make_user_token(user.id, tenant_id)
    _set_auth_cookie(response, jwt_token)

    return AuthResponse(
        user=UserOut(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            tenant_id=tenant_id,
            plan=plan,
            email_verified=user.email_verified,
        ),
        token=jwt_token,
    )


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    from ai_receptionist.services.email.sendgrid_service import send_password_reset_email

    email = body.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()

    # Always return success to prevent email enumeration
    if user and user.email_verified:
        token = secrets.token_urlsafe(32)
        user.password_reset_token = token
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        send_password_reset_email(email, token)

    return {"ok": True, "message": "If an account exists with that email, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    if len(body.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters.")

    user = db.query(User).filter(User.password_reset_token == body.token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link.")

    if user.password_reset_expires and datetime.utcnow() > user.password_reset_expires:
        raise HTTPException(status_code=400, detail="This reset link has expired. Please request a new one.")

    user.password_hash = hash_password(body.password)
    user.password_reset_token = None
    user.password_reset_expires = None
    db.commit()

    return {"ok": True, "message": "Password updated. You can now log in."}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.owner_user_id == user.id).first()
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        tenant_id=tenant.id if tenant else None,
        plan=tenant.plan if tenant else None,
        email_verified=user.email_verified,
    )


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key=_COOKIE_NAME, path="/")
    return {"ok": True}
