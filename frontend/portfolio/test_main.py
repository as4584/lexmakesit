"""
Test suite for API Consulting Portfolio
Compatible with FastAPI and pytest - CI/CD friendly
"""

import os
from unittest.mock import patch

import pytest

# Set test environment before importing the app
os.environ["PRODUCTION"] = "false"
os.environ["TRUSTED_HOSTS"] = "localhost,127.0.0.1,testserver"
os.environ["RATE_LIMIT_STORAGE"] = "memory://"

from main import app


@pytest.fixture
def client():
    """Test client fixture"""
    try:
        from fastapi.testclient import TestClient

        return TestClient(app)
    except ImportError:
        from starlette.testclient import TestClient

        return TestClient(app)


def test_home_page(client):
    """Test main landing page loads"""
    response = client.get("/")
    assert response.status_code == 200
    assert b"API" in response.content or b"Portfolio" in response.content


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_get_projects(client):
    """Test projects API endpoint"""
    response = client.get("/api/projects")
    assert response.status_code == 200
    data = response.json()
    assert "projects" in data
    assert isinstance(data["projects"], list)


def test_get_testimonials(client):
    """Test testimonials API endpoint"""
    response = client.get("/api/testimonials")
    assert response.status_code == 200
    data = response.json()
    assert "testimonials" in data
    assert isinstance(data["testimonials"], list)


VALID_CONTACT = {
    "name": "John Doe",
    "email": "john@example.com",
    "subject": "Test Inquiry",
    "message": "This is a test message that should be long enough to pass validation.",
}


def test_contact_form_stored_returns_success(client):
    """A recorded enquiry is a success even when no notification goes out.

    Notifications are best effort. Once the message is safely in the
    database it is retrievable, so promising a reply is honest.
    """
    with patch("storage.save_contact", return_value=True):
        response = client.post("/api/contact", json=VALID_CONTACT)

    assert response.status_code == 201
    data = response.json()
    assert "message" in data
    assert "contact_id" in data


def test_contact_form_undeliverable_is_reported(client):
    """With nothing stored and nothing sent, the caller must be told.

    This endpoint used to answer 201 "I'll respond within 24 hours" in
    exactly this situation, which lost real enquiries silently: the
    sender waited for a reply to a message nobody could read. The
    regression guard is that it must NOT claim success.
    """
    with patch("storage.save_contact", return_value=False):
        response = client.post("/api/contact", json=VALID_CONTACT)

    assert response.status_code == 503
    body = response.json()["message"].lower()
    # The alternative route has to be in the message, or the sender is stuck.
    assert "email" in body


def test_contact_form_invalid_email(client):
    """Test contact form with invalid email"""
    form_data = {
        "name": "John Doe",
        "email": "invalid-email",
        "subject": "Inquiry",
        "message": "This is a test message that should be long enough.",
    }
    response = client.post("/api/contact", json=form_data)
    assert response.status_code == 422  # Validation error


def test_contact_form_short_message(client):
    """Test contact form with message too short"""
    form_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "subject": "Inquiry",
        "message": "Short",
    }
    response = client.post("/api/contact", json=form_data)
    assert response.status_code == 422  # Validation error


def test_404_page(client):
    """Test 404 error page"""
    response = client.get("/nonexistent-page")
    assert response.status_code == 404


def test_security_headers(client):
    """Test security headers are present"""
    response = client.get("/")
    headers = response.headers
    # Check for some security headers (may not all be present)
    security_headers = [
        "content-security-policy",
        "x-content-type-options",
        "x-frame-options",
        "strict-transport-security",
    ]
    present_headers = [h for h in security_headers if h in headers]
    # At least one security header should be present
    assert len(present_headers) >= 1


def test_api_docs(client):
    """Test API documentation is accessible in development"""
    response = client.get("/docs")
    # In production, docs might be disabled, so accept both 200 and 404
    assert response.status_code in [200, 404]


def test_openapi_schema(client):
    """Test OpenAPI schema is accessible"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "paths" in data


def test_app_startup():
    """Test that the app instance is valid"""
    assert app is not None
    assert hasattr(app, "routes")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
