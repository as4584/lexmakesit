"""
Tests for /api/voice/* endpoints:
  - provider activation when selecting an ElevenLabs voice
  - provider switch back when selecting an OpenAI voice
  - GET /current returns correct provider state
  - 401 on unauthenticated requests uses new error messages
  - CORS preflight from dashboard.lexmakesit.com is accepted
"""

from __future__ import annotations

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
from ai_receptionist.models.tenant import Tenant
from ai_receptionist.models.user import User


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def ping(self) -> bool:
        return True

    def exists(self, key: str) -> int:
        return 1 if key in self.store else 0

    def setex(self, key: str, ttl_seconds: int, value: str) -> bool:
        self.store[key] = value
        return True

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def incr(self, key: str) -> int:
        value = int(self.store.get(key, "0")) + 1
        self.store[key] = str(value)
        return value

    def expire(self, key: str, ttl_seconds: int) -> bool:
        return True

    def delete(self, key: str) -> int:
        return 1 if self.store.pop(key, None) is not None else 0


@pytest.fixture()
def _test_engine(monkeypatch: pytest.MonkeyPatch):
    """Create an in-memory SQLite engine shared across the test's fixtures."""
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret")
    monkeypatch.setenv("ADMIN_PRIVATE_KEY", "test-admin-secret")

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[User.__table__, Business.__table__, Tenant.__table__, EmailToken.__table__],
    )
    yield engine
    Base.metadata.drop_all(
        bind=engine,
        tables=[User.__table__, Business.__table__, Tenant.__table__, EmailToken.__table__],
    )


@pytest.fixture()
def session_factory(_test_engine):
    """Return a SQLAlchemy session factory bound to the test engine."""
    return sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    fake_redis = FakeRedis()
    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(auth_api, "_get_redis_client", lambda: fake_redis)
    auth_api._redis_client = None

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _register_and_login(
    client: TestClient,
    email: str = "voice@example.com",
    session_factory=None,
) -> str:
    """Sign up and return the access token.

    If *session_factory* is given, also seeds a Tenant row for the new user
    so that voice endpoints (which require a Tenant) succeed.
    """
    resp = client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": "pass1234",
            "full_name": "Voice User",
            "business_name": "Voice Biz",
        },
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    if session_factory is not None:
        _seed_tenant(session_factory, email)
    return token


def _seed_tenant(session_factory, email: str) -> None:
    """Insert a Tenant row for the user with *email* into the test DB."""
    db = session_factory()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None, f"User {email} not found after signup"
        # id is a slug string PK — derive a unique one from the email local part
        slug = email.split("@")[0].replace(".", "-")
        tenant = Tenant(
            id=slug,
            name="Test Tenant",
            owner_user_id=user.id,
            tts_provider="openai",
            openai_voice="shimmer",
        )
        db.add(tenant)
        db.commit()
    finally:
        db.close()


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Provider activation — ElevenLabs
# ---------------------------------------------------------------------------


def test_select_elevenlabs_voice_activates_provider(client: TestClient, session_factory):
    """PUT /api/voice/select must set tts_provider='elevenlabs'."""
    token = _register_and_login(client, "el-select@example.com", session_factory=session_factory)

    resp = client.put(
        "/api/voice/select",
        json={"voice_id": "el_abc123", "voice_name": "Luna"},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # Verify provider is now elevenlabs
    current = client.get("/api/voice/current", headers=_auth_headers(token))
    assert current.status_code == 200
    data = current.json()
    assert data["tts_provider"] == "elevenlabs"
    assert data["elevenlabs_voice_id"] == "el_abc123"
    assert data["elevenlabs_voice_name"] == "Luna"


# ---------------------------------------------------------------------------
# Provider switch — OpenAI
# ---------------------------------------------------------------------------


def test_select_openai_voice_switches_provider_back(client: TestClient, session_factory):
    """PUT /api/voice/openai-voice must set tts_provider='openai'."""
    token = _register_and_login(
        client, "openai-select@example.com", session_factory=session_factory
    )

    # First set ElevenLabs so the switch is meaningful
    client.put(
        "/api/voice/select",
        json={"voice_id": "el_xyz", "voice_name": "Aria"},
        headers=_auth_headers(token),
    )

    resp = client.put(
        "/api/voice/openai-voice",
        json={"voice": "nova"},
        headers=_auth_headers(token),
    )
    # "nova" is not in OPENAI_VOICES — expect 422
    assert resp.status_code == 422

    resp = client.put(
        "/api/voice/openai-voice",
        json={"voice": "alloy"},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["openai_voice"] == "alloy"

    current = client.get("/api/voice/current", headers=_auth_headers(token))
    data = current.json()
    assert data["tts_provider"] == "openai"
    assert data["openai_voice"] == "alloy"


# ---------------------------------------------------------------------------
# GET /current defaults
# ---------------------------------------------------------------------------


def test_get_current_voice_defaults_for_fresh_tenant(client: TestClient, session_factory):
    """Newly created tenant should report openai provider with shimmer voice."""
    token = _register_and_login(client, "fresh@example.com", session_factory=session_factory)

    resp = client.get("/api/voice/current", headers=_auth_headers(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["tts_provider"] == "openai"
    assert data["openai_voice"] == "shimmer"
    assert data["elevenlabs_voice_id"] is None
    assert data["has_clone"] is False


# ---------------------------------------------------------------------------
# 401 error messages
# ---------------------------------------------------------------------------


def test_unauthenticated_voice_browse_returns_authentication_required(client: TestClient):
    """GET /api/voice/browse without credentials must 401 with 'authentication required'."""
    resp = client.get("/api/voice/browse")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "authentication required"


def test_unauthenticated_voice_select_returns_authentication_required(client: TestClient):
    """PUT /api/voice/select without credentials must 401 with 'authentication required'."""
    resp = client.put("/api/voice/select", json={"voice_id": "x", "voice_name": "X"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "authentication required"


def test_malformed_bearer_header_returns_invalid_format(client: TestClient):
    """A malformed Authorization header should return 'invalid Authorization header format'."""
    resp = client.get(
        "/api/voice/current",
        headers={"Authorization": "not-bearer-format"},
    )
    assert resp.status_code == 401
    assert "invalid" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# CORS — dashboard origin
# ---------------------------------------------------------------------------


def test_cors_preflight_from_dashboard_origin(client: TestClient):
    """OPTIONS preflight from dashboard.lexmakesit.com must be accepted."""
    resp = client.options(
        "/api/voice/current",
        headers={
            "Origin": "https://dashboard.lexmakesit.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert resp.status_code in (200, 204)
    acao = resp.headers.get("access-control-allow-origin", "")
    assert acao in ("https://dashboard.lexmakesit.com", "*")


def test_authenticated_request_from_dashboard_origin(client: TestClient, session_factory):
    """Authenticated GET /api/voice/current from dashboard origin should include ACAO header."""
    token = _register_and_login(client, "dash-cors@example.com", session_factory=session_factory)
    resp = client.get(
        "/api/voice/current",
        headers={
            **_auth_headers(token),
            "Origin": "https://dashboard.lexmakesit.com",
        },
    )
    assert resp.status_code == 200
    acao = resp.headers.get("access-control-allow-origin", "")
    assert acao in ("https://dashboard.lexmakesit.com", "*")
