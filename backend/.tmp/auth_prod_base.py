"""
API endpoints for frontend authentication and user management.

Includes:
- Signup/Login with JWT tokens
- Token refresh and revocation
- Email verification
- Password reset
"""
import secrets
import hashlib
import importlib
import os
import time
from uuid import uuid4
from datetime import datetime, timedelta
from typing import Any, Optional

import jwt
from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
import bcrypt
import logging

from ai_receptionist.core.database import get_db
from ai_receptionist.core.auth import get_current_user, TokenData
from ai_receptionist.config.settings import get_settings
from ai_receptionist.models.user import User
from ai_receptionist.models.business import Business
from ai_receptionist.models.email_token import EmailToken

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Token expirations
EMAIL_TOKEN_EXPIRY_MINUTES = 30
ACCESS_TOKEN_EXPIRE_MINUTES = 60
LOGIN_FAIL_LIMIT = 5
LOGIN_FAIL_WINDOW_SECONDS = 15 * 60
_redis_client: Optional[Any] = None


# ============================================================================
# Request/Response Models
# ============================================================================

class SignupRequest(BaseModel):
    """Sign up request payload."""
    email: EmailStr
    password: str
    full_name: str
    business_name: str


class LoginRequest(BaseModel):
    """Login request payload."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Authentication token response."""
    access_token: str
    token_type: str = "bearer"
    user: dict


class RefreshResponse(BaseModel):
    """Token refresh response."""
    access_token: str
    token_type: str = "bearer"


class VerifyEmailRequest(BaseModel):
    """Email verification request."""
    token: str


class ForgotPasswordRequest(BaseModel):
    """Forgot password request."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Password reset request."""
    token: str
    new_password: str


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str


# ============================================================================
# Token Utilities
# ============================================================================


def _jwt_key() -> str:
    settings = get_settings()
    if settings.jwt_secret_key:
        return settings.jwt_secret_key
    if settings.admin_private_key:
        logger.warning("JWT_SECRET_KEY not configured; falling back to ADMIN_PRIVATE_KEY")
        return settings.admin_private_key
    raise HTTPException(status_code=500, detail="JWT signing key not configured")


def _get_redis_client() -> Optional[Any]:
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    try:
        redis_module = importlib.import_module("redis")
    except Exception:
        logger.warning("Redis package not installed; auth state will be stateless")
        return None

    settings = get_settings()
    try:
        _redis_client = redis_module.Redis.from_url(
            settings.get_redis_url(),
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        _redis_client.ping()
        return _redis_client
    except Exception as exc:
        logger.warning("Redis unavailable for auth state; proceeding stateless: %s", exc)
        return None


def _revoked_jti_key(jti: str) -> str:
    return f"revoked_jti:{jti}"


def _failed_login_key(email: str) -> str:
    return f"login_fails:{email.lower()}"


def _extract_bearer_token(authorization: Optional[str]) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    return authorization.split(" ", 1)[1]


def _is_token_revoked(payload: dict[str, Any]) -> bool:
    jti = payload.get("jti")
    if not jti:
        return False

    client = _get_redis_client()
    if not client:
        return False

    try:
        return bool(client.exists(_revoked_jti_key(str(jti))))
    except Exception as exc:
        logger.warning("Failed to check revoked token state: %s", exc)
        return False


def _revoke_token(payload: dict[str, Any]) -> None:
    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti or not exp:
        return

    client = _get_redis_client()
    if not client:
        return

    ttl_seconds = max(int(exp) - int(time.time()), 1)
    try:
        client.setex(_revoked_jti_key(str(jti)), ttl_seconds, "1")
    except Exception as exc:
        logger.warning("Failed to revoke token jti=%s: %s", jti, exc)


def _failed_login_count(email: str) -> int:
    client = _get_redis_client()
    if not client:
        return 0
    try:
        value = client.get(_failed_login_key(email))
        return int(value or 0)
    except Exception as exc:
        logger.warning("Failed to read login failure count for %s: %s", email, exc)
        return 0


def _record_failed_login(email: str) -> int:
    client = _get_redis_client()
    if not client:
        return 0
    key = _failed_login_key(email)
    try:
        attempts = client.incr(key)
        client.expire(key, LOGIN_FAIL_WINDOW_SECONDS)
        return int(attempts)
    except Exception as exc:
        logger.warning("Failed to store login failure for %s: %s", email, exc)
        return 0


def _clear_failed_logins(email: str) -> None:
    client = _get_redis_client()
    if not client:
        return
    try:
        client.delete(_failed_login_key(email))
    except Exception as exc:
        logger.warning("Failed to clear login failure counter for %s: %s", email, exc)


def _make_access_token(user_id: int, email: str, business_id: Optional[str]) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "user_id": user_id,
        "email": email,
        "business_id": business_id,
        "jti": str(uuid4()),
        "iat": now,
        "nbf": now - 30,
        "exp": now + (ACCESS_TOKEN_EXPIRE_MINUTES * 60),
    }
    return jwt.encode(payload, _jwt_key(), algorithm="HS256")


def _decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, _jwt_key(), algorithms=["HS256"])
        if _is_token_revoked(payload):
            raise HTTPException(status_code=401, detail="invalid or expired token")
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="invalid or expired token")


def _extract_token_from_request(request: Request, authorization: Optional[str]) -> str:
    if authorization:
        return _extract_bearer_token(authorization)
    cookie_token = request.cookies.get("lex_token")
    if cookie_token:
        return cookie_token
    raise HTTPException(status_code=401, detail="missing bearer token")

def generate_token() -> str:
    """Generate a secure URL-safe token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash a token using SHA256."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_email_token(
    db: Session,
    user_id: int,
    token_type: str
) -> str:
    """
    Create and store an email token.
    
    Args:
        db: Database session
        user_id: User ID
        token_type: 'verify_email' or 'reset_password'
        
    Returns:
        The plaintext token (for sending via email)
    """
    # Generate plaintext token
    plaintext_token = generate_token()
    token_hash = hash_token(plaintext_token)
    
    # Invalidate any existing tokens of the same type for this user
    db.query(EmailToken).filter(
        EmailToken.user_id == user_id,
        EmailToken.token_type == token_type,
        EmailToken.used_at.is_(None)
    ).update({"used_at": datetime.utcnow()})
    
    # Create new token
    email_token = EmailToken(
        user_id=user_id,
        token_type=token_type,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(minutes=EMAIL_TOKEN_EXPIRY_MINUTES)
    )
    db.add(email_token)
    db.commit()
    
    return plaintext_token


def verify_email_token(
    db: Session,
    plaintext_token: str,
    token_type: str
) -> Optional[EmailToken]:
    """
    Verify an email token and mark it as used.
    
    Args:
        db: Database session
        plaintext_token: The plaintext token from the URL
        token_type: Expected token type
        
    Returns:
        The EmailToken if valid, None otherwise
    """
    token_hash = hash_token(plaintext_token)
    
    email_token = db.query(EmailToken).filter(
        EmailToken.token_hash == token_hash,
        EmailToken.token_type == token_type
    ).first()
    
    if not email_token:
        return None
    
    if not email_token.is_valid:
        return None
    
    # Mark as used
    email_token.used_at = datetime.utcnow()
    db.commit()
    
    return email_token


# ============================================================================
# Authentication Endpoints
# ============================================================================

@router.post("/signup", response_model=TokenResponse)
async def signup(request: SignupRequest, db: Session = Depends(get_db)):
    """
    Create a new user account and business.
    
    This endpoint:
    1. Creates a user account
    2. Creates a business linked to the user
    3. Sends email verification
    4. Returns a JWT token for immediate login
    """
    # Check if user exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    password_hash = bcrypt.hashpw(
        request.password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')
    
    # Create user
    user = User(
        email=request.email,
        password_hash=password_hash,
        full_name=request.full_name,
        is_verified=False
    )
    db.add(user)
    db.flush()
    
    # Create business
    business = Business(
        owner_email=user.email,
        name=request.business_name,
        subscription_status='trial'
    )
    db.add(business)
    db.commit()
    
    # Create verification token and send email
    try:
        plaintext_token = create_email_token(db, user.id, "verify_email")
        logger.info(f"Verification token created for {user.email}: {plaintext_token[:8]}...")
    except Exception as e:
        logger.error(f"Failed to create verification token: {e}")
        # Don't fail signup if email fails
    
    # Create JWT token
    token = _make_access_token(user.id, user.email, str(business.id))
    
    return TokenResponse(
        access_token=token,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "business_id": str(business.id),
            "is_verified": user.is_verified
        }
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email and password.
    """
    if _failed_login_count(request.email) >= LOGIN_FAIL_LIMIT:
        logger.warning("brute-force lockout triggered for %s", request.email)
        raise HTTPException(status_code=429, detail="too many failed login attempts")

    # Find user
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        attempts = _record_failed_login(request.email)
        if attempts >= LOGIN_FAIL_LIMIT:
            raise HTTPException(status_code=429, detail="too many failed login attempts")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not bcrypt.checkpw(request.password.encode('utf-8'), user.password_hash.encode('utf-8')):
        attempts = _record_failed_login(request.email)
        if attempts >= LOGIN_FAIL_LIMIT:
            raise HTTPException(status_code=429, detail="too many failed login attempts")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    
    # Get user's business
    business = db.query(Business).filter(Business.owner_email == user.email).first()
    business_id = str(business.id) if business else None

    _clear_failed_logins(request.email)
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    # Create token
    token = _make_access_token(user.id, user.email, business_id)
    
    return TokenResponse(
        access_token=token,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "business_id": business_id,
            "is_verified": user.is_verified
        }
    )


@router.get("/me")
async def get_current_user_info(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    """
    Get current authenticated user information.
    """
    token = _extract_token_from_request(request, authorization)
    payload = _decode_access_token(token)
    user_id = int(payload.get("user_id") or 0)
    business_id = payload.get("business_id")

    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "user_id": user_id,
        "email": db_user.email,
        "full_name": db_user.full_name,
        "business_id": business_id,
        "is_verified": db_user.is_verified
    }


@router.post("/logout")
async def logout(request: Request, authorization: Optional[str] = Header(default=None)):
    """
    Logout (client-side token removal).
    """
    token = _extract_token_from_request(request, authorization)
    payload = _decode_access_token(token)
    _revoke_token(payload)
    return {"message": "Logged out successfully"}


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    token = _extract_token_from_request(request, authorization)
    payload = _decode_access_token(token)

    user_id = int(payload.get("user_id") or 0)
    email = str(payload.get("email") or "")
    business_id = payload.get("business_id")

    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user or not db_user.is_active:
        raise HTTPException(status_code=401, detail="user not found or inactive")

    new_token = _make_access_token(user_id, email, business_id)
    return RefreshResponse(access_token=new_token)


# ============================================================================
# Email Verification Endpoints
# ============================================================================

@router.post("/request-verify-email", response_model=MessageResponse)
async def request_verify_email(
    user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Request a new email verification link.
    
    Requires authentication. Sends a verification email to the user's email address.
    """
    db_user = db.query(User).filter(User.id == user.user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if db_user.is_verified:
        return MessageResponse(message="Email is already verified")
    
    # Create token (email delivery not wired in this deployment branch)
    plaintext_token = create_email_token(db, db_user.id, "verify_email")
    logger.info(f"Verification token created for {db_user.email}: {plaintext_token[:8]}...")
    
    # Always return success to prevent email enumeration
    return MessageResponse(message="If the email exists, a verification link has been sent")


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    """
    Verify a user's email address using the token from the email link.
    """
    email_token = verify_email_token(db, request.token, "verify_email")
    
    if not email_token:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification link"
        )
    
    # Mark user as verified
    user = db.query(User).filter(User.id == email_token.user_id).first()
    if user:
        user.is_verified = True
        user.email_verified_at = datetime.utcnow()
        db.commit()
        logger.info(f"User {user.email} verified their email")
    
    return MessageResponse(message="Email verified successfully")


# ============================================================================
# Password Reset Endpoints
# ============================================================================

@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Request a password reset link.
    
    ALWAYS returns a generic 200 response to prevent email enumeration.
    """
    user = db.query(User).filter(User.email == request.email).first()
    
    if user and user.is_active:
        # Create token and send email
        try:
            plaintext_token = create_email_token(db, user.id, "reset_password")
            logger.info(f"Password reset token created for {user.email}: {plaintext_token[:8]}...")
        except Exception as e:
            logger.error(f"Failed to create password reset token: {e}")
    else:
        logger.debug(f"Password reset requested for unknown/inactive email: {request.email}")
    
    # ALWAYS return generic success message (security: prevent email enumeration)
    return MessageResponse(
        message="If an account exists with this email, a password reset link has been sent"
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset password using a valid token.
    """
    # Validate password
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long"
        )
    
    # Verify token
    email_token = verify_email_token(db, request.token, "reset_password")
    
    if not email_token:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset link"
        )
    
    # Update password
    user = db.query(User).filter(User.id == email_token.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid reset link")
    
    # Hash new password
    password_hash = bcrypt.hashpw(
        request.new_password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')
    
    user.password_hash = password_hash
    db.commit()
    
    logger.info(f"Password reset completed for user {user.email}")
    
    return MessageResponse(message="Password reset successfully")
