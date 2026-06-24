import io
import json
import zipfile
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from main import app
from db import SessionLocal, User, set_user_api_key, clear_user_api_key, set_history_enabled, get_user_history

client = TestClient(app)

CLAUDE_KEY = "sk-test-claude"
CHATGPT_KEY = "sk-test-chatgpt"
GEMINI_KEY = "sk-test-gemini"


def _set_key(provider: str, key: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.google_id == "test-google-id").one()
        set_user_api_key(db, user, provider, key)
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _logged_in():
    fake_token = {"access_token": "fake", "userinfo": {
        "sub": "test-google-id",
        "email": "tester@example.com",
        "name": "Tester",
        "picture": "",
    }}
    with patch("main.oauth.google.authorize_access_token", AsyncMock(return_value=fake_token)):
        client.get("/auth/google/callback")
    client.headers["X-CSRF-Token"] = client.get("/api/me").json()["csrf_token"]
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.google_id == "test-google-id").one()
        set_user_api_key(db, user, "claude", CLAUDE_KEY)
        clear_user_api_key(db, user, "chatgpt")
        clear_user_api_key(db, user, "gemini")
    finally:
        db.close()


def test_analyze_endpoint_requires_login():
    anon_client = TestClient(app)
    resp = anon_client.post("/analyze", json={"code": "x = 1"})
    assert resp.status_code == 200
    assert "Giriş yapmanız gerekiyor" in resp.json()["error"]


def test_analyze_endpoint_rejects_missing_csrf_token():
    resp = client.post("/analyze", json={"code": "x = 1"}, headers={"X-CSRF-Token": ""})
    assert "CSRF" in resp.json()["error"]


def test_analyze_endpoint_rejects_wrong_csrf_token():
    resp = client.post("/analyze", json={"code": "x = 1"}, headers={"X-CSRF-Token": "wrong-token"})
    assert "CSRF" in resp.json()["error"]


def test_analyze_endpoint_rate_limits_after_threshold():
    import main
    with patch("main.analyze_code_collab", AsyncMock(return_value="ok")):
        for _ in range(main.ANALYSIS_RATE_LIMIT):
            resp = client.post("/analyze", json={"code": "x = 1"})
            assert "error" not in resp.json()
        resp = client.post("/analyze", json={"code": "x = 1"})
    assert "Çok fazla istek" in resp.json()["error"]


def test_upload_rate_limit_is_independent_of_analyze():
    import main
    with patch("main.analyze_code_collab", AsyncMock(return_value="ok")):
        for _ in range(main.ANALYSIS_RATE_LIMIT):
            client.post("/analyze", json={"code": "x = 1"})
        # /analyze artık limitte, ama /upload kendi bucket'ında olmalı
        resp = client.post("/upload", files={"file": ("app.py", b"print(1)", "text/x-python")})
    assert "error" not in resp.json()


def test_root_serves_login_page_when_not_authenticated():
    anon_client = TestClient(app)
    resp = anon_client.get("/")
    assert resp.status_code == 200
    assert "Google ile Giriş Yap" in resp.text


def test_privacy_page_is_public_without_login():
    anon_client = TestClient(app)
    resp = anon_client.get("/gizlilik")
    assert resp.status_code == 200
    assert "Verilerinle ne yapıyoruz" in resp.text


def test_root_serves_app_when_authenticated():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "VaultScan" in resp.text
    assert "providerPicker" in resp.text


def test_settings_page_requires_login():
    anon_client = TestClient(app)
    resp = anon_client.get("/settings")
    assert resp.status_code == 200
    assert "Google ile Giriş Yap" in resp.text


def test_settings_page_serves_when_authenticated():
    resp = client.get("/settings")
    assert resp.status_code == 200
    assert "API Key" in resp.text
    assert "key-card" in resp.text


def test_analyze_endpoint_returns_mocked_result():
    with patch("main.analyze_code_collab", AsyncMock(return_value="<div>mocked</div>")) as mock_analyze:
        resp = client.post("/analyze", json={"code": "print(1)", "language": "Python"})
    assert resp.status_code == 200
    assert resp.json() == {"type": "result", "result": "<div>mocked</div>"}
    mock_analyze.assert_called_once_with("print(1)", "Python", ["claude"], {"claude": CLAUDE_KEY})


def test_analyze_endpoint_default_language():
    with patch("main.analyze_code_collab", AsyncMock(return_value="ok")) as mock_analyze:
        client.post("/analyze", json={"code": "x = 1"})
    mock_analyze.assert_called_once_with("x = 1", "otomatik tespit", ["claude"], {"claude": CLAUDE_KEY})


def test_analyze_endpoint_saves_history_when_enabled():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.google_id == "test-google-id").one()
        set_history_enabled(db, user, True)
    finally:
        db.close()

    with patch("main.analyze_code_collab", AsyncMock(return_value="<div>saved</div>")):
        client.post("/analyze", json={"code": "print(1)", "language": "Python"})

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.google_id == "test-google-id").one()
        history = get_user_history(db, user)
        assert history[0].result_html == "<div>saved</div>"
        assert history[0].source_type == "paste"
        assert history[0].providers == "claude"
    finally:
        db.close()


def test_analyze_endpoint_saves_severity_counts_computed_from_badges():
    mocked_result = (
        '<div class="finding"><span class="badge badge-critical">kritik</span></div>'
        '<div class="finding"><span class="badge badge-high">yüksek</span></div>'
        '<div class="finding"><span class="badge badge-high">yüksek</span></div>'
    )
    with patch("main.analyze_code_collab", AsyncMock(return_value=mocked_result)):
        client.post("/analyze", json={"code": "print(1)", "language": "Python"})

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.google_id == "test-google-id").one()
        history = get_user_history(db, user)
        assert history[0].severity_counts == "1,2,0,0"
    finally:
        db.close()


def test_analyze_endpoint_skips_history_when_disabled():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.google_id == "test-google-id").one()
        set_history_enabled(db, user, False)
        before = len(get_user_history(db, user))
    finally:
        db.close()

    with patch("main.analyze_code_collab", AsyncMock(return_value="<div>not-saved</div>")):
        client.post("/analyze", json={"code": "print(1)", "language": "Python"})

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.google_id == "test-google-id").one()
        after = len(get_user_history(db, user))
        set_history_enabled(db, user, True)  # diğer testler için varsayılana döndür
    finally:
        db.close()
    assert after == before


def test_analyze_endpoint_unknown_provider_returns_error():
    resp = client.post("/analyze", json={"code": "x = 1", "providers": ["not-a-real-provider"]})
    assert resp.status_code == 200
    assert "Bilinmeyen AI" in resp.json()["error"]


def test_analyze_endpoint_empty_providers_returns_error():
    resp = client.post("/analyze", json={"code": "x = 1", "providers": []})
    assert resp.status_code == 200
    assert "En az bir AI" in resp.json()["error"]


def test_analyze_endpoint_rejects_oversized_code():
    import main
    too_big = "x" * (main.MAX_PASTE_LENGTH + 1)
    resp = client.post("/analyze", json={"code": too_big})
    assert resp.status_code == 200
    assert "çok büyük" in resp.json()["error"]


def test_analyze_endpoint_unconfigured_provider_returns_friendly_error():
    resp = client.post("/analyze", json={"code": "x = 1", "providers": ["gemini"]})
    assert resp.status_code == 200
    assert "kendi API key'inizi eklemediniz" in resp.json()["error"]


def test_analyze_endpoint_explicit_providers_passed_through():
    _set_key("chatgpt", CHATGPT_KEY)
    with patch("main.analyze_code_collab", AsyncMock(return_value="<div>gpt</div>")) as mock_analyze:
        resp = client.post("/analyze", json={"code": "x = 1", "providers": ["chatgpt"]})
    assert resp.json() == {"type": "result", "result": "<div>gpt</div>"}
    mock_analyze.assert_called_once_with("x = 1", "otomatik tespit", ["chatgpt"], {"chatgpt": CHATGPT_KEY})


def test_analyze_endpoint_multi_provider_list_passed_through():
    _set_key("chatgpt", CHATGPT_KEY)
    _set_key("gemini", GEMINI_KEY)
    with patch("main.analyze_code_collab", AsyncMock(return_value="<div>merged</div>")) as mock_analyze:
        resp = client.post("/analyze", json={"code": "x = 1", "providers": ["claude", "chatgpt", "gemini"]})
    assert resp.json() == {"type": "result", "result": "<div>merged</div>"}
    mock_analyze.assert_called_once_with(
        "x = 1", "otomatik tespit", ["claude", "chatgpt", "gemini"],
        {"claude": CLAUDE_KEY, "chatgpt": CHATGPT_KEY, "gemini": GEMINI_KEY},
    )


def test_analyze_endpoint_collab_exception_returns_friendly_error():
    with patch("main.analyze_code_collab", AsyncMock(side_effect=RuntimeError("Hiçbir AI analizi tamamlayamadı."))):
        resp = client.post("/analyze", json={"code": "x = 1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "error"
    assert "Analiz hatası" in data["message"]


def test_upload_single_file():
    with patch("main.analyze_code_collab", AsyncMock(return_value="<div>single</div>")) as mock_analyze:
        resp = client.post(
            "/upload",
            files={"file": ("app.py", b"print('hi')", "text/x-python")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "result"
    assert data["result_type"] == "file"
    assert data["result"] == "<div>single</div>"
    mock_analyze.assert_called_once_with("print('hi')", "PY", ["claude"], {"claude": CLAUDE_KEY})


def test_upload_single_file_saves_history():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.google_id == "test-google-id").one()
        set_history_enabled(db, user, True)
    finally:
        db.close()

    with patch("main.analyze_code_collab", AsyncMock(return_value="<div>single</div>")):
        client.post("/upload", files={"file": ("app.py", b"print('hi')", "text/x-python")})

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.google_id == "test-google-id").one()
        history = get_user_history(db, user)
        assert history[0].source_type == "file"
        assert history[0].source_label == "app.py"
        assert history[0].result_html == "<div>single</div>"
    finally:
        db.close()


def test_upload_rejects_missing_csrf_token():
    resp = client.post(
        "/upload",
        files={"file": ("app.py", b"print(1)", "text/x-python")},
        headers={"X-CSRF-Token": ""},
    )
    assert "CSRF" in resp.json()["error"]


def test_upload_endpoint_requires_login():
    anon_client = TestClient(app)
    resp = anon_client.post("/upload", files={"file": ("app.py", b"print(1)", "text/x-python")})
    assert resp.status_code == 200
    assert "Giriş yapmanız gerekiyor" in resp.json()["error"]


def test_upload_unsupported_extension():
    resp = client.post("/upload", files={"file": ("malware.exe", b"binary", "application/octet-stream")})
    assert resp.status_code == 200
    assert "error" in resp.json()


def test_upload_unconfigured_provider_returns_friendly_error_before_parsing():
    resp = client.post(
        "/upload",
        files={"file": ("app.py", b"print('hi')", "text/x-python")},
        data={"providers": "gemini"},
    )
    assert resp.status_code == 200
    assert "kendi API key'inizi eklemediniz" in resp.json()["error"]


def test_upload_comma_separated_providers_parsed_into_list():
    _set_key("chatgpt", CHATGPT_KEY)
    with patch("main.analyze_code_collab", AsyncMock(return_value="<div>multi-ai</div>")) as mock_analyze:
        resp = client.post(
            "/upload",
            files={"file": ("app.py", b"print('hi')", "text/x-python")},
            data={"providers": "claude, chatgpt"},
        )
    assert resp.json()["result"] == "<div>multi-ai</div>"
    mock_analyze.assert_called_once_with(
        "print('hi')", "PY", ["claude", "chatgpt"], {"claude": CLAUDE_KEY, "chatgpt": CHATGPT_KEY}
    )


def test_upload_zip_multiple_small_files_analyzed_together():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("main.py", "print('a')")
        zf.writestr("utils.py", "print('b')")
    buf.seek(0)

    with patch("main.analyze_multi_collab", AsyncMock(return_value="<div>zip-result</div>")) as mock_multi:
        resp = client.post("/upload", files={"file": ("project.zip", buf.getvalue(), "application/zip")})

    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "result"
    assert data["result_type"] == "zip"
    assert len(data["results"]) == 2
    assert all(r["result"] == "<div>zip-result</div>" for r in data["results"])
    assert mock_multi.call_args.args[1] == ["claude"]
    assert mock_multi.call_args.args[2] == {"claude": CLAUDE_KEY}
    assert len(mock_multi.call_args.args[0]) == 2


def test_upload_zip_processes_every_group_not_just_the_first():
    buf = io.BytesIO()
    big_file = "print(1)\n" * 1500  # ~13500 karakter, MAX_GROUP_SIZE=30000'in altında
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("a.py", big_file)
        zf.writestr("b.py", big_file)
        zf.writestr("c.py", big_file)
    buf.seek(0)

    with patch("main.analyze_multi_collab", AsyncMock(return_value="<div>multi</div>")) as mock_multi, \
         patch("main.analyze_code_collab", AsyncMock(return_value="<div>single</div>")) as mock_single:
        resp = client.post("/upload", files={"file": ("project.zip", buf.getvalue(), "application/zip")})

    data = resp.json()
    assert data["type"] == "result"
    assert data["result_type"] == "zip"
    # a.py + b.py ilk grupta (birlikte ~27000 karakter), c.py kendi grubunda
    # önceden c.py'nin grubu hiç işlenmiyordu (break bug'ı)
    assert len(data["results"]) == 3
    assert {r["file"] for r in data["results"]} == {"a.py", "b.py", "c.py"}
    mock_multi.assert_called_once()
    mock_single.assert_called_once()


def test_upload_rejects_file_over_max_size():
    big_content = b"x" * (10 * 1024 * 1024 + 1)
    resp = client.post("/upload", files={"file": ("big.py", big_content, "text/x-python")})
    assert resp.status_code == 200
    assert "çok büyük" in resp.json()["error"]


def test_upload_zip_skips_oversized_entry():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("huge.py", "x = 1\n" * 400000)  # ~2.4 MB, MAX_ZIP_ENTRY_SIZE'ı aşar
        zf.writestr("small.py", "print('hi')")
    buf.seek(0)

    with patch("main.analyze_code_collab", AsyncMock(return_value="<div>single</div>")) as mock_single:
        resp = client.post("/upload", files={"file": ("project.zip", buf.getvalue(), "application/zip")})

    data = resp.json()
    assert data["type"] == "result"
    assert data["result_type"] == "zip"
    assert len(data["results"]) == 1
    assert data["results"][0]["file"] == "small.py"
    mock_single.assert_called_once()


def test_github_endpoint_requires_login():
    anon_client = TestClient(app)
    resp = anon_client.post("/github", json={"url": "https://github.com/owner/repo"})
    assert resp.status_code == 200
    assert "Giriş yapmanız gerekiyor" in resp.json()["error"]


def test_github_invalid_url_returns_error_without_streaming():
    resp = client.post("/github", json={"url": "not-a-github-url"})
    assert resp.status_code == 200
    assert resp.json() == {"error": "Geçersiz GitHub URL'i."}


def test_github_unconfigured_provider_returns_error_without_streaming():
    resp = client.post("/github", json={"url": "https://github.com/owner/repo", "providers": ["gemini"]})
    assert resp.status_code == 200
    assert "kendi API key'inizi eklemediniz" in resp.json()["error"]


@respx.mock
def test_github_repo_not_found_yields_error_message():
    respx.get("https://api.github.com/repos/owner/repo/git/trees/HEAD").mock(
        return_value=httpx.Response(404)
    )
    resp = client.post("/github", json={"url": "https://github.com/owner/repo"})
    lines = [json.loads(l) for l in resp.text.strip().splitlines()]
    assert lines[0]["type"] == "error"
    assert "owner/repo" in lines[0]["message"]


@respx.mock
def test_github_invalid_token_yields_token_error():
    respx.get("https://api.github.com/repos/owner/repo/git/trees/HEAD").mock(
        return_value=httpx.Response(401)
    )
    resp = client.post("/github", json={"url": "https://github.com/owner/repo", "token": "bad"})
    lines = [json.loads(l) for l in resp.text.strip().splitlines()]
    assert lines[0] == {"type": "error", "message": "GitHub token geçersiz veya süresi dolmuş."}


@respx.mock
def test_github_rate_limit_yields_rate_limit_message():
    respx.get("https://api.github.com/repos/owner/repo/git/trees/HEAD").mock(
        return_value=httpx.Response(403, headers={"X-RateLimit-Remaining": "0"})
    )
    resp = client.post("/github", json={"url": "https://github.com/owner/repo"})
    lines = [json.loads(l) for l in resp.text.strip().splitlines()]
    assert lines[0]["type"] == "error"
    assert "rate limit" in lines[0]["message"].lower()


@respx.mock
def test_github_happy_path_streams_progress_and_result():
    tree = {"tree": [{"path": "main.py", "type": "blob", "size": 100}]}
    respx.get("https://api.github.com/repos/owner/repo/git/trees/HEAD").mock(
        return_value=httpx.Response(200, json=tree)
    )
    respx.get("https://raw.githubusercontent.com/owner/repo/HEAD/main.py").mock(
        return_value=httpx.Response(200, text="print('hello')")
    )

    with patch("main.analyze_code_collab", AsyncMock(return_value="<div>found nothing</div>")) as mock_analyze:
        resp = client.post("/github", json={"url": "https://github.com/owner/repo"})

    lines = [json.loads(l) for l in resp.text.strip().splitlines()]
    types = [l["type"] for l in lines]
    assert types[0] == "start"
    assert "progress" in types
    assert "result" in types
    assert types[-1] == "done"
    assert mock_analyze.call_args.args[:4] == ("print('hello')", "PY", ["claude"], {"claude": CLAUDE_KEY})
    assert "owner/repo" in mock_analyze.call_args.args[4]


@respx.mock
def test_github_happy_path_saves_one_history_entry():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.google_id == "test-google-id").one()
        set_history_enabled(db, user, True)
    finally:
        db.close()

    tree = {"tree": [{"path": "main.py", "type": "blob", "size": 100}]}
    respx.get("https://api.github.com/repos/owner/repo/git/trees/HEAD").mock(
        return_value=httpx.Response(200, json=tree)
    )
    respx.get("https://raw.githubusercontent.com/owner/repo/HEAD/main.py").mock(
        return_value=httpx.Response(200, text="print('hello')")
    )

    with patch("main.analyze_code_collab", AsyncMock(return_value="<div>found nothing</div>")):
        client.post("/github", json={"url": "https://github.com/owner/repo"})

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.google_id == "test-google-id").one()
        history = get_user_history(db, user)
        assert history[0].source_type == "github"
        assert history[0].source_label == "owner/repo"
        assert "main.py" in history[0].result_html
        assert "found nothing" in history[0].result_html
    finally:
        db.close()


@respx.mock
def test_github_max_files_is_clamped_to_upper_bound():
    tree = {"tree": [{"path": f"f{i}.py", "type": "blob", "size": 100} for i in range(60)]}
    respx.get("https://api.github.com/repos/owner/repo/git/trees/HEAD").mock(
        return_value=httpx.Response(200, json=tree)
    )
    respx.get(url__regex=r"https://raw\.githubusercontent\.com/owner/repo/HEAD/f\d+\.py").mock(
        return_value=httpx.Response(200, text="print('x')")
    )

    resp = client.post("/github", json={"url": "https://github.com/owner/repo", "max_files": 1000})
    lines = [json.loads(l) for l in resp.text.strip().splitlines()]
    start = next(l for l in lines if l["type"] == "start")
    assert start["total"] == 50


@respx.mock
def test_github_multi_provider_selection_is_passed_to_collab():
    tree = {"tree": [{"path": "main.py", "type": "blob", "size": 100}]}
    respx.get("https://api.github.com/repos/owner/repo/git/trees/HEAD").mock(
        return_value=httpx.Response(200, json=tree)
    )
    respx.get("https://raw.githubusercontent.com/owner/repo/HEAD/main.py").mock(
        return_value=httpx.Response(200, text="print('hello')")
    )

    _set_key("gemini", GEMINI_KEY)
    with patch("main.analyze_code_collab", AsyncMock(return_value="<div>merged</div>")) as mock_analyze:
        resp = client.post("/github", json={"url": "https://github.com/owner/repo", "providers": ["claude", "gemini"]})

    lines = [json.loads(l) for l in resp.text.strip().splitlines()]
    assert any(l["type"] == "result" and l["result"] == "<div>merged</div>" for l in lines)
    assert mock_analyze.call_args.args[:4] == (
        "print('hello')", "PY", ["claude", "gemini"], {"claude": CLAUDE_KEY, "gemini": GEMINI_KEY}
    )


@respx.mock
def test_github_no_files_downloaded_yields_error():
    tree = {"tree": [{"path": "main.py", "type": "blob", "size": 100}]}
    respx.get("https://api.github.com/repos/owner/repo/git/trees/HEAD").mock(
        return_value=httpx.Response(200, json=tree)
    )
    respx.get("https://raw.githubusercontent.com/owner/repo/HEAD/main.py").mock(
        return_value=httpx.Response(500)
    )

    resp = client.post("/github", json={"url": "https://github.com/owner/repo"})
    lines = [json.loads(l) for l in resp.text.strip().splitlines()]
    error_lines = [l for l in lines if l["type"] == "error"]
    assert error_lines
    assert "indirilemedi" in error_lines[-1]["message"]
