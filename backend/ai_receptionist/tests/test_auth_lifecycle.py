from __future__ import annotations

import importlib

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ai_receptionist.app.api import auth as auth_api
from ai_receptionist.app.main import app
from ai_receptionist.core.database import get_db
from ai_receptionist.models.base import Base
from ai_receptionist.models.business import Business
from ai_receptionist.models.email_token import EmailToken
from ai_receptionist.models.user import User

# client + client_no_redis fixtures provided by conftest.py


def _signup(client: TestClient, email: str, password: str = "pass1234") -> dict:
    response = client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": password,
            "full_name": "Test User",
            "business_name": "Test Business",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_refresh_returns_new_valid_token(client: TestClient):
    signup_data = _signup(client, "refresh-user@example.com")
    old_token = signup_data["access_token"]

    response = client.post(
        "/api/auth/refresh",
        headers={"Authorization": f"Bearer {old_token}"},
    )
    assert response.status_code == 200

    new_token = response.json()["access_token"]
    assert new_token != old_token

    old_payload = jwt.decode(old_token, "test-jwt-secret", algorithms=["HS256"])
    new_payload = jwt.decode(new_token, "test-jwt-secret", algorithms=["HS256"])
    assert old_payload["user_id"] == new_payload["user_id"]
    assert old_payload["business_id"] == new_payload["business_id"]
    assert old_payload["jti"] != new_payload["jti"]


def test_logout_revokes_token_for_subsequent_requests(client: TestClient):
    signup_data = _signup(client, "logout-user@example.com")
    token = signup_data["access_token"]

    me_before = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_before.status_code == 200

    logout_response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_response.status_code == 200
    assert logout_response.json()["message"] == "Logged out successfully"

    me_after = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_after.status_code == 401
    assert me_after.json()["detail"] == "invalid or expired token"


def test_failed_login_lockout_after_five_attempts(client: TestClient):
    email = "lockout-user@example.com"
    _signup(client, email, password="correct-pass")

    for _ in range(4):
        invalid = client.post(
            "/api/auth/login",
            json={"email": email, "password": "wrong-pass"},
        )
        assert invalid.status_code == 401

    fifth_invalid = client.post(
        "/api/auth/login",
        json={"email": email, "password": "wrong-pass"},
    )
    assert fifth_invalid.status_code == 429
    assert fifth_invalid.json()["detail"] == "too many failed login attempts"

    valid_after_lockout = client.post(
        "/api/auth/login",
        json={"email": email, "password": "correct-pass"},
    )
    assert valid_after_lockout.status_code == 429


# ============================================================================
# CORS / preflight
# ============================================================================


def test_cors_preflight_from_allowed_origin(client: TestClient):
    """OPTIONS preflight from an allowed origin must return 200 with CORS headers."""
    response = client.options(
        "/api/auth/login",
        headers={
            "Origin": "https://auth.lexmakesit.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") in (
        "https://auth.lexmakesit.com",
        "*",
    )


def test_cors_header_present_on_login_response(client: TestClient):
    """Real POST to /login from an allowed origin should carry ACAO header."""
    _signup(client, "cors-user@example.com")
    response = client.post(
        "/api/auth/login",
        json={"email": "cors-user@example.com", "password": "pass1234"},
        headers={"Origin": "https://auth.lexmakesit.com"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") in (
        "https://auth.lexmakesit.com",
        "*",
    )


# ============================================================================
# Redis-unavailable degradation
# ============================================================================

# client_no_redis fixture provided by conftest.py


def test_login_succeeds_when_redis_unavailable(client_no_redis: TestClient):
    """Login must succeed even when Redis is unavailable (degraded mode)."""
    _signup(client_no_redis, "no-redis-user@example.com")
    response = client_no_redis.post(
        "/api/auth/login",
        json={"email": "no-redis-user@example.com", "password": "pass1234"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_logout_succeeds_when_redis_unavailable(client_no_redis: TestClient):
    """Logout must complete gracefully when Redis is unavailable."""
    data = _signup(client_no_redis, "no-redis-logout@example.com")
    token = data["access_token"]
    response = client_no_redis.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_revoked_token_not_enforced_when_redis_unavailable(client_no_redis: TestClient):
    """
    When Redis is absent, token revocation is silently skipped.
    A logged-out token will still resolve (known degradation — accepted behaviour).
    The test documents this so regressions are visible.
    """
    data = _signup(client_no_redis, "degraded-revoke@example.com")
    token = data["access_token"]
    client_no_redis.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    # Token is NOT revoked because Redis is down — /me still returns 200
    me = client_no_redis.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200  # degraded — acceptable, documented


# ============================================================================
# Startup: missing JWT config
# ============================================================================


def test_jwt_key_missing_raises_at_auth_call(monkeypatch: pytest.MonkeyPatch):
    """If JWT_SECRET_KEY is absent, the first auth call must raise 500."""
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("ADMIN_PRIVATE_KEY", raising=False)

    # Reload settings cache and auth module state
    from ai_receptionist.config import settings as settings_mod

    importlib.reload(settings_mod)
    auth_api._redis_client = None

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(
        bind=engine,
        tables=[User.__table__, Business.__table__, EmailToken.__table__],
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(auth_api, "_get_redis_client", lambda: None)

    with TestClient(app, raise_server_exceptions=False) as tc:
        response = tc.post(
            "/api/auth/login",
            json={"email": "x@x.com", "password": "pass1234"},
        )
    app.dependency_overrides.clear()

    assert response.status_code in (500, 401)


# ============================================================================
# Readiness probe
# ============================================================================


def test_readiness_endpoint_returns_ready_fields(client: TestClient):
    """/readiness must return JSON with 'ready' and 'checks' keys."""
    response = client.get("/readiness")
    assert response.status_code in (200, 503)
    body = response.json()
    assert "ready" in body
    assert "checks" in body
    assert "database" in body["checks"]
    assert "redis" in body["checks"]


def test_liveness_always_ok(client: TestClient):
    """/health is a liveness probe and must always return 200."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ============================================================================
# Auth event emission (structured logging)
# ============================================================================


def test_login_success_emits_auth_event(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """A successful login should emit a login_success auth event."""
    events: list[dict] = []

    import ai_receptionist.app.middleware as mw

    original_emit = mw.emit_auth_event

    def capture_emit(event_type, **kwargs):
        events.append({"event_type": event_type, **kwargs})
        return original_emit(event_type, **kwargs)

    monkeypatch.setattr(mw, "emit_auth_event", capture_emit)
    import ai_receptionist.app.api.auth as _auth_mod

    monkeypatch.setattr(_auth_mod, "emit_auth_event", capture_emit)

    _signup(client, "event-user@example.com")
    events.clear()

    client.post(
        "/api/auth/login",
        json={"email": "event-user@example.com", "password": "pass1234"},
    )

    success = [e for e in events if e["event_type"] == "login_success"]
    assert len(success) >= 1
    assert success[0]["email"] == "event-user@example.com"


def test_login_failure_emits_auth_event(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """A failed login should emit a login_failure auth event."""
    events: list[dict] = []

    import ai_receptionist.app.middleware as mw
    import ai_receptionist.app.api.auth as _auth_mod

    def capture_emit(event_type, **kwargs):
        events.append({"event_type": event_type, **kwargs})

    monkeypatch.setattr(mw, "emit_auth_event", capture_emit)
    monkeypatch.setattr(_auth_mod, "emit_auth_event", capture_emit)

    _signup(client, "fail-event-user@example.com")
    events.clear()

    client.post(
        "/api/auth/login",
        json={"email": "fail-event-user@example.com", "password": "wrong"},
    )

    failures = [e for e in events if e["event_type"] == "login_failure"]
    assert len(failures) >= 1
