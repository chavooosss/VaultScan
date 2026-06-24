from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from db import SessionLocal, User, get_user_api_key, clear_user_api_key

client = TestClient(app)


@pytest.fixture(autouse=True)
def _logged_in():
    fake_token = {"access_token": "fake", "userinfo": {
        "sub": "keys-test-google-id",
        "email": "keystester@example.com",
        "name": "Keys Tester",
        "picture": "",
    }}
    with patch("main.oauth.google.authorize_access_token", AsyncMock(return_value=fake_token)):
        client.get("/auth/google/callback")
    client.headers["X-CSRF-Token"] = client.get("/api/me").json()["csrf_token"]
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.google_id == "keys-test-google-id").one()
        for provider in ("claude", "chatgpt", "gemini"):
            clear_user_api_key(db, user, provider)
    finally:
        db.close()


def test_get_keys_requires_login():
    anon_client = TestClient(app)
    resp = anon_client.get("/api/keys")
    assert "Giriş yapmanız gerekiyor" in resp.json()["error"]


def test_get_keys_reports_false_when_none_set():
    resp = client.get("/api/keys")
    assert resp.json() == {"claude": False, "chatgpt": False, "gemini": False}


def test_post_key_saves_it_and_get_reflects_it():
    resp = client.post("/api/keys", json={"provider": "claude", "api_key": "sk-ant-real-looking-key"})
    assert resp.json() == {"ok": True}

    resp = client.get("/api/keys")
    assert resp.json()["claude"] is True
    assert resp.json()["chatgpt"] is False


def test_post_key_never_returns_raw_value():
    resp = client.post("/api/keys", json={"provider": "gemini", "api_key": "super-secret-value"})
    assert "super-secret-value" not in resp.text

    resp = client.get("/api/keys")
    assert "super-secret-value" not in resp.text


def test_post_key_is_encrypted_at_rest():
    client.post("/api/keys", json={"provider": "chatgpt", "api_key": "sk-openai-real-looking-key"})

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.google_id == "keys-test-google-id").one()
        assert user.openai_api_key_enc != "sk-openai-real-looking-key"
        assert get_user_api_key(user, "chatgpt") == "sk-openai-real-looking-key"
    finally:
        db.close()


def test_post_key_rejects_missing_csrf_token():
    resp = client.post(
        "/api/keys",
        json={"provider": "claude", "api_key": "x"},
        headers={"X-CSRF-Token": ""},
    )
    assert "CSRF" in resp.json()["error"]


def test_post_key_rejects_unknown_provider():
    resp = client.post("/api/keys", json={"provider": "not-a-real-provider", "api_key": "x"})
    assert "Bilinmeyen AI" in resp.json()["error"]


def test_post_key_rejects_empty_value():
    resp = client.post("/api/keys", json={"provider": "claude", "api_key": "   "})
    assert "boş olamaz" in resp.json()["error"]


def test_delete_key_removes_it():
    client.post("/api/keys", json={"provider": "claude", "api_key": "sk-to-be-removed"})
    resp = client.delete("/api/keys/claude")
    assert resp.json() == {"ok": True}

    resp = client.get("/api/keys")
    assert resp.json()["claude"] is False


def test_delete_key_rejects_unknown_provider():
    resp = client.delete("/api/keys/not-a-real-provider")
    assert "Bilinmeyen AI" in resp.json()["error"]


def test_keys_endpoints_require_login():
    anon_client = TestClient(app)
    assert "Giriş yapmanız gerekiyor" in anon_client.post(
        "/api/keys", json={"provider": "claude", "api_key": "x"}
    ).json()["error"]
    assert "Giriş yapmanız gerekiyor" in anon_client.delete("/api/keys/claude").json()["error"]
