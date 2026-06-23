from unittest.mock import AsyncMock, patch

from authlib.integrations.base_client.errors import OAuthError
from fastapi.testclient import TestClient
from starlette.responses import RedirectResponse

from main import app
from db import SessionLocal, User

client = TestClient(app)


def test_login_redirects_to_google():
    fake_authorize_redirect = AsyncMock(
        return_value=RedirectResponse(url="https://accounts.google.com/o/oauth2/v2/auth?fake=1")
    )
    with patch("main.oauth.google.authorize_redirect", fake_authorize_redirect):
        resp = client.get("/auth/google/login", follow_redirects=False)

    assert resp.status_code in (302, 307)
    assert "accounts.google.com" in resp.headers["location"]


def test_callback_creates_user_and_sets_session_then_redirects_home():
    fake_token = {"access_token": "fake", "userinfo": {
        "sub": "google-123",
        "email": "test@example.com",
        "name": "Test User",
        "picture": "https://example.com/pic.png",
    }}
    with patch("main.oauth.google.authorize_access_token", AsyncMock(return_value=fake_token)):
        resp = client.get("/auth/google/callback", follow_redirects=False)

    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "/"
    assert resp.cookies.get("session") is not None


def test_callback_reuses_same_user_on_repeat_login():
    fake_token = {"access_token": "fake", "userinfo": {
        "sub": "google-456",
        "email": "again@example.com",
        "name": "Again User",
        "picture": "",
    }}
    with patch("main.oauth.google.authorize_access_token", AsyncMock(return_value=fake_token)):
        client.get("/auth/google/callback", follow_redirects=False)
        client.get("/auth/google/callback", follow_redirects=False)

    db = SessionLocal()
    try:
        count = db.query(User).filter(User.google_id == "google-456").count()
    finally:
        db.close()
    assert count == 1


def test_callback_handles_oauth_failure_without_crashing():
    with patch("main.oauth.google.authorize_access_token", AsyncMock(side_effect=OAuthError("denied"))):
        resp = client.get("/auth/google/callback", follow_redirects=False)

    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "/?login_error=1"


def test_logout_clears_session_and_redirects_home():
    resp = client.get("/auth/logout", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "/"


def test_me_endpoint_reports_unauthenticated_without_session():
    anon_client = TestClient(app)
    resp = anon_client.get("/api/me")
    assert resp.json() == {"authenticated": False}


def test_me_endpoint_reports_user_info_after_login():
    fake_token = {"access_token": "fake", "userinfo": {
        "sub": "google-789",
        "email": "me@example.com",
        "name": "Me User",
        "picture": "https://example.com/me.png",
    }}
    with patch("main.oauth.google.authorize_access_token", AsyncMock(return_value=fake_token)):
        client.get("/auth/google/callback", follow_redirects=False)

    resp = client.get("/api/me")
    assert resp.json() == {
        "authenticated": True,
        "name": "Me User",
        "picture": "https://example.com/me.png",
    }
