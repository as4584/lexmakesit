"""
Call Health Test Suite — guards the call pipeline against silent breakage.

These tests specifically address the failure modes that took down production:

  1. websockets package missing from Docker image  →  uvicorn silently rejects
     all WebSocket upgrades with 404.  Every call drops instantly.

  2. ElevenLabs API key absent  →  /api/voice/browse returns 500 instead of an
     empty list, crashing the Voice Library UI.

  3. /twilio/voice returns invalid or missing TwiML  →  Twilio can't connect the
     call to the stream.

  4. /twilio/stream WebSocket route not registered  →  404, call drops.

Run with: poetry run pytest -q tests/test_call_health.py
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

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
# Fixtures (minimal in-memory DB, no external services needed)
# ---------------------------------------------------------------------------


class _FakeRedis:
    def __init__(self) -> None:
        self._store: dict = {}

    def ping(self) -> bool:
        return True

    def exists(self, key: str) -> int:
        return 1 if key in self._store else 0

    def setex(self, key: str, ttl: int, value: str) -> bool:
        self._store[key] = value
        return True

    def get(self, key: str):
        return self._store.get(key)

    def incr(self, key: str) -> int:
        v = int(self._store.get(key, "0")) + 1
        self._store[key] = str(v)
        return v

    def expire(self, key: str, ttl: int) -> bool:
        return True

    def delete(self, key: str) -> int:
        return 1 if self._store.pop(key, None) is not None else 0


@pytest.fixture()
def _engine(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "ci-health-secret")
    monkeypatch.setenv("ADMIN_PRIVATE_KEY", "ci-admin-secret")

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[
            User.__table__,
            Business.__table__,
            Tenant.__table__,
            EmailToken.__table__,
        ],
    )
    yield engine
    Base.metadata.drop_all(
        bind=engine,
        tables=[
            User.__table__,
            Business.__table__,
            Tenant.__table__,
            EmailToken.__table__,
        ],
    )


@pytest.fixture()
def _session_factory(_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, _session_factory):
    def _override_db():
        db = _session_factory()
        try:
            yield db
        finally:
            db.close()

    fake_redis = _FakeRedis()
    app.dependency_overrides[get_db] = _override_db
    monkeypatch.setattr(auth_api, "_get_redis_client", lambda: fake_redis)
    auth_api._redis_client = None

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def _signup_and_login(client: TestClient, email: str, sf) -> str:
    """Register a user and return its JWT access token."""
    resp = client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": "Test1234!",
            "full_name": "Health Test",
            "business_name": "Health Biz",
        },
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]

    # Seed a Tenant row so voice endpoints succeed
    db = sf()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user
        slug = email.split("@")[0].replace(".", "-")
        tenant = Tenant(
            id=slug,
            name="Health Tenant",
            owner_user_id=user.id,
            tts_provider="openai",
            openai_voice="shimmer",
        )
        db.add(tenant)
        db.commit()
    finally:
        db.close()

    return token


# ===========================================================================
# 1. Dependency / package smoke tests
# ===========================================================================


def test_websockets_library_is_importable():
    """websockets must be installed — its absence caused the production outage.

    Uvicorn logs a warning and silently rejects ALL WebSocket upgrades if
    neither 'websockets' nor 'wsproto' is importable.  This test catches a
    missing dependency *before* the image is deployed.
    """
    import importlib

    ws = importlib.import_module("websockets")
    assert hasattr(ws, "__version__"), "websockets imported but has no __version__"


def test_cryptography_library_is_importable():
    """cryptography must be installed — its absence prevents backend startup.

    encryption.py imports PBKDF2HMAC from cryptography.hazmat.  If the package
    is missing the process fails to start and EVERY endpoint returns
    'Failed to fetch' (including the auth login page).
    """
    import importlib

    cr = importlib.import_module("cryptography")
    assert hasattr(cr, "__version__"), "cryptography imported but has no __version__"


def test_aiohttp_library_is_importable():
    """aiohttp is required by realtime.py (OpenAI WebSocket client)."""
    import importlib

    importlib.import_module("aiohttp")


# ===========================================================================
# 2. Health endpoints
# ===========================================================================


def test_health_endpoint_returns_ok(client: TestClient):
    """GET /health must return HTTP 200 with {status: 'ok'}."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"


# ===========================================================================
# 3. Twilio voice webhook — TwiML correctness
# ===========================================================================


def test_twilio_voice_webhook_returns_xml(client: TestClient):
    """POST /twilio/voice must return HTTP 200 with XML content-type."""
    resp = client.post(
        "/twilio/voice",
        data={
            "CallSid": "CA_health_test_000",
            "From": "+15550001111",
            "To": "+12298215986",
        },
    )
    assert resp.status_code == 200
    ct = resp.headers.get("content-type", "")
    assert "xml" in ct, f"Expected XML content-type, got: {ct}"


def test_twilio_voice_twiml_is_valid_xml(client: TestClient):
    """TwiML response body must be parseable XML."""
    resp = client.post(
        "/twilio/voice",
        data={
            "CallSid": "CA_health_test_001",
            "From": "+15550001111",
            "To": "+12298215986",
        },
    )
    assert resp.status_code == 200
    # Raises if not valid XML
    root = ET.fromstring(resp.text)
    assert root.tag == "Response", f"Root TwiML tag should be 'Response', got: {root.tag}"


def test_twilio_voice_twiml_contains_stream_connect(client: TestClient):
    """TwiML must include <Connect><Stream url="..."> to bridge the call."""
    resp = client.post(
        "/twilio/voice",
        data={
            "CallSid": "CA_health_test_002",
            "From": "+15550001111",
            "To": "+12298215986",
        },
    )
    root = ET.fromstring(resp.text)

    connect = root.find("Connect")
    assert connect is not None, "TwiML missing <Connect> — call will never reach AI"

    stream = connect.find("Stream")
    assert stream is not None, "TwiML missing <Stream> inside <Connect>"

    url = stream.get("url", "")
    assert url.startswith("wss://"), f"Stream URL must use wss://, got: {url}"


def test_twilio_voice_twiml_stream_url_includes_to_param(client: TestClient):
    """Stream URL must include ?to= so the WS handler loads the correct tenant."""
    resp = client.post(
        "/twilio/voice",
        data={
            "CallSid": "CA_health_test_003",
            "From": "+15550001111",
            "To": "+12298215986",
        },
    )
    root = ET.fromstring(resp.text)
    stream_url = root.find("Connect/Stream").get("url", "")
    assert (
        "to=" in stream_url
    ), f"Stream URL missing '?to=' param — tenant lookup will fail. URL: {stream_url}"


# ===========================================================================
# 4. WebSocket route registration
# ===========================================================================


def test_websocket_stream_route_is_registered(client: TestClient):
    """GET /twilio/stream without WebSocket upgrade must return 400 or 403.

    A 404 would mean the route isn't registered at all — that's the bug
    that killed production (wrong prefix or missing router include).
    """
    resp = client.get("/twilio/stream?to=%2B12298215986")
    # 400 = FastAPI's rejection of a non-WS request to a WS route  (correct)
    # 403 = auth wall before WS upgrade                             (acceptable)
    # 404 = route not registered                                    (FAIL — bug!)
    assert resp.status_code != 404, (
        "/twilio/stream returned 404 — the route is not registered. "
        "Check that realtime_router is included in main.py with the correct prefix."
    )


# ===========================================================================
# 5. Voice Library API — graceful degradation
# ===========================================================================


def test_voice_browse_without_auth_returns_401(client: TestClient):
    """GET /api/voice/browse without a token must return 401."""
    resp = client.get("/api/voice/browse")
    assert resp.status_code == 401


def test_voice_browse_without_elevenlabs_key_returns_empty_list(
    client: TestClient, _session_factory
):
    """GET /api/voice/browse must return [] (not 500) when ElevenLabs is unconfigured.

    This was the exact behaviour causing 'Failed to fetch' in the UI.
    The fix: _get_elevenlabs_optional() catches RuntimeError and returns None,
    and browse_voices() returns [] when el is None.
    """
    token = _signup_and_login(client, "browse-health@example.com", _session_factory)
    # ELEVENLABS_API_KEY is not set in the CI env — service raises RuntimeError
    resp = client.get(
        "/api/voice/browse",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert (
        resp.status_code == 200
    ), f"Expected 200 (empty list) when ElevenLabs key is absent, got {resp.status_code}: {resp.text}"
    assert resp.json() == [], f"Expected [] when ElevenLabs key is absent, got: {resp.json()}"


def test_voice_current_returns_200_for_authenticated_user(client: TestClient, _session_factory):
    """GET /api/voice/current must return the tenant's current voice settings."""
    token = _signup_and_login(client, "current-health@example.com", _session_factory)
    resp = client.get(
        "/api/voice/current",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "tts_provider" in data
    assert "openai_voice" in data


def test_openai_voice_select_saves_provider(client: TestClient, _session_factory):
    """PUT /api/voice/openai-voice must persist tts_provider='openai'."""
    token = _signup_and_login(client, "oai-health@example.com", _session_factory)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.put(
        "/api/voice/openai-voice",
        json={"voice": "alloy"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    current = client.get("/api/voice/current", headers=headers).json()
    assert current["tts_provider"] == "openai"
    assert current["openai_voice"] == "alloy"


def test_openai_voice_preview_invalid_voice_returns_422(client: TestClient, _session_factory):
    """GET /api/voice/openai-preview/<bad_voice> must return 422."""
    token = _signup_and_login(client, "preview-health@example.com", _session_factory)
    resp = client.get(
        "/api/voice/openai-preview/not_a_real_voice",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
