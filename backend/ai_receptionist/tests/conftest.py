"""
Pytest configuration and shared fixtures for ai_receptionist tests.

All fixtures that are used across more than one test module live here.
Tests that need a TestClient should use `client` (FakeRedis, SQLite in-memory).
Tests that specifically exercise Redis-unavailable degradation use `client_no_redis`.
"""

from __future__ import annotations

from pathlib import Path

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

# Path helpers
PROJECT_ROOT = Path(__file__).parent.parent.parent

# All tables used by any test in this suite — cheaper to create together once
_TEST_TABLES = [
    User.__table__,
    Business.__table__,
    Tenant.__table__,
    EmailToken.__table__,
]


# ---------------------------------------------------------------------------
# In-memory Redis stub
# ---------------------------------------------------------------------------


class FakeRedis:
    """Drop-in Redis stub backed by a plain dict.

    Implements every method called by auth.py (ping, exists, setex, get,
    incr, expire, delete). No external service required.
    """

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def ping(self) -> bool:
        return True

    def exists(self, key: str) -> int:
        return 1 if key in self._store else 0

    def setex(self, key: str, ttl: int, value: str) -> bool:
        self._store[key] = value
        return True

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def incr(self, key: str) -> int:
        v = int(self._store.get(key, "0")) + 1
        self._store[key] = str(v)
        return v

    def expire(self, key: str, ttl: int) -> bool:
        return True

    def delete(self, key: str) -> int:
        return 1 if self._store.pop(key, None) is not None else 0


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def _db_engine(monkeypatch: pytest.MonkeyPatch):
    """SQLite in-memory engine with every test-suite table created.

    Also sets required environment variables so the settings singleton
    initialises without hitting real secrets.
    """
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret")
    monkeypatch.setenv("ADMIN_PRIVATE_KEY", "test-admin-secret")

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=_TEST_TABLES)
    yield engine
    Base.metadata.drop_all(bind=engine, tables=_TEST_TABLES)


@pytest.fixture()
def _session_factory(_db_engine):
    """SQLAlchemy session factory bound to the in-memory test database."""
    return sessionmaker(autocommit=False, autoflush=False, bind=_db_engine)


# ---------------------------------------------------------------------------
# TestClient fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, _session_factory):
    """FastAPI TestClient wired to SQLite + FakeRedis.

    Suitable for every test that exercises the HTTP API without needing
    a real Postgres or Redis instance.
    """

    def _override_db():
        db = _session_factory()
        try:
            yield db
        finally:
            db.close()

    fake_redis = FakeRedis()
    app.dependency_overrides[get_db] = _override_db
    monkeypatch.setattr(auth_api, "_get_redis_client", lambda: fake_redis)
    auth_api._redis_client = None

    with TestClient(app) as tc:
        yield tc

    app.dependency_overrides.clear()


@pytest.fixture()
def client_no_redis(monkeypatch: pytest.MonkeyPatch, _session_factory):
    """FastAPI TestClient where Redis is explicitly unavailable (returns None).

    Use this fixture to test graceful degradation when Redis is down.
    Token revocation and rate-limiting do not work in this mode — that
    is documented intentional behaviour.
    """

    def _override_db():
        db = _session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db
    monkeypatch.setattr(auth_api, "_get_redis_client", lambda: None)
    auth_api._redis_client = None

    with TestClient(app) as tc:
        yield tc

    app.dependency_overrides.clear()
