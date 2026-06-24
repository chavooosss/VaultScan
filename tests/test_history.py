from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from db import SessionLocal, User, Analysis, save_analysis, set_history_enabled, get_or_create_user

client = TestClient(app)


@pytest.fixture(autouse=True)
def _logged_in():
    fake_token = {"access_token": "fake", "userinfo": {
        "sub": "history-test-google-id",
        "email": "historytester@example.com",
        "name": "History Tester",
        "picture": "",
    }}
    with patch("main.oauth.google.authorize_access_token", AsyncMock(return_value=fake_token)):
        client.get("/auth/google/callback")
    client.headers["X-CSRF-Token"] = client.get("/api/me").json()["csrf_token"]
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.google_id == "history-test-google-id").one()
        set_history_enabled(db, user, True)
        # her testten önce bu kullanıcının geçmişini temizle (paylaşılan test DB'si)
        db.query(Analysis).filter(Analysis.user_id == user.id).delete()
        db.commit()
    finally:
        db.close()


def test_list_history_requires_login():
    anon_client = TestClient(app)
    resp = anon_client.get("/api/history")
    assert "Giriş yapmanız gerekiyor" in resp.json()["error"]


def test_list_history_empty_for_new_user():
    resp = client.get("/api/history")
    data = resp.json()
    assert data["history_enabled"] is True
    assert data["items"] == []


def test_list_history_returns_saved_entries_without_full_result():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.google_id == "history-test-google-id").one()
        save_analysis(db, user, ["claude", "gemini"], "paste", "Yapıştırılan kod", "<div>full report</div>")
    finally:
        db.close()

    resp = client.get("/api/history")
    data = resp.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["source_type"] == "paste"
    assert item["source_label"] == "Yapıştırılan kod"
    assert item["providers"] == ["claude", "gemini"]
    assert "result" not in item


def test_get_history_item_returns_full_result():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.google_id == "history-test-google-id").one()
        analysis = save_analysis(db, user, ["claude"], "file", "app.py", "<div>full report</div>")
        analysis_id = analysis.id
    finally:
        db.close()

    resp = client.get(f"/api/history/{analysis_id}")
    data = resp.json()
    assert data["result"] == "<div>full report</div>"
    assert data["source_label"] == "app.py"


def test_get_history_item_rejects_other_users_entry():
    db = SessionLocal()
    try:
        other = get_or_create_user(db, google_id="other-history-user", email="o@b.com", name="Other")
        analysis = save_analysis(db, other, ["claude"], "paste", "Kod", "<div>secret</div>")
        analysis_id = analysis.id
    finally:
        db.close()

    resp = client.get(f"/api/history/{analysis_id}")
    assert "bulunamadı" in resp.json()["error"]


def test_delete_history_item_removes_it():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.google_id == "history-test-google-id").one()
        analysis = save_analysis(db, user, ["claude"], "paste", "Kod", "<div>x</div>")
        analysis_id = analysis.id
    finally:
        db.close()

    resp = client.delete(f"/api/history/{analysis_id}")
    assert resp.json() == {"ok": True}

    resp = client.get(f"/api/history/{analysis_id}")
    assert "bulunamadı" in resp.json()["error"]


def test_delete_history_item_rejects_missing_csrf_token():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.google_id == "history-test-google-id").one()
        analysis = save_analysis(db, user, ["claude"], "paste", "Kod", "<div>x</div>")
        analysis_id = analysis.id
    finally:
        db.close()

    resp = client.delete(f"/api/history/{analysis_id}", headers={"X-CSRF-Token": ""})
    assert "CSRF" in resp.json()["error"]


def test_history_endpoints_require_login():
    anon_client = TestClient(app)
    assert "Giriş yapmanız gerekiyor" in anon_client.get("/api/history/1").json()["error"]
    assert "Giriş yapmanız gerekiyor" in anon_client.delete("/api/history/1").json()["error"]


def test_toggle_history_off_then_on():
    resp = client.post("/api/history/toggle", json={"enabled": False})
    assert resp.json() == {"ok": True, "history_enabled": False}
    assert client.get("/api/history").json()["history_enabled"] is False

    resp = client.post("/api/history/toggle", json={"enabled": True})
    assert resp.json() == {"ok": True, "history_enabled": True}
    assert client.get("/api/history").json()["history_enabled"] is True


def test_toggle_history_requires_login():
    anon_client = TestClient(app)
    resp = anon_client.post("/api/history/toggle", json={"enabled": False})
    assert "Giriş yapmanız gerekiyor" in resp.json()["error"]


def test_toggle_history_rejects_missing_csrf_token():
    resp = client.post(
        "/api/history/toggle",
        json={"enabled": False},
        headers={"X-CSRF-Token": ""},
    )
    assert "CSRF" in resp.json()["error"]
