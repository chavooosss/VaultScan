import io
import json
import zipfile
from unittest.mock import patch

import httpx
import respx
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_analyze_endpoint_returns_mocked_result():
    with patch("main.analyze_code", return_value="<div>mocked</div>") as mock_analyze:
        resp = client.post("/analyze", json={"code": "print(1)", "language": "Python"})
    assert resp.status_code == 200
    assert resp.json() == {"result": "<div>mocked</div>"}
    mock_analyze.assert_called_once_with("print(1)", "Python", provider="claude")


def test_analyze_endpoint_default_language():
    with patch("main.analyze_code", return_value="ok") as mock_analyze:
        client.post("/analyze", json={"code": "x = 1"})
    mock_analyze.assert_called_once_with("x = 1", "otomatik tespit", provider="claude")


def test_analyze_endpoint_unknown_provider_returns_error():
    resp = client.post("/analyze", json={"code": "x = 1", "provider": "not-a-real-provider"})
    assert resp.status_code == 200
    assert "Bilinmeyen AI" in resp.json()["error"]


def test_analyze_endpoint_unconfigured_provider_returns_friendly_error():
    with patch("main.is_configured", return_value=False):
        resp = client.post("/analyze", json={"code": "x = 1", "provider": "gemini"})
    assert resp.status_code == 200
    assert "yapılandırılmamış" in resp.json()["error"]


def test_analyze_endpoint_explicit_provider_is_passed_through():
    with patch("main.is_configured", return_value=True), \
         patch("main.analyze_code", return_value="<div>gpt</div>") as mock_analyze:
        resp = client.post("/analyze", json={"code": "x = 1", "provider": "chatgpt"})
    assert resp.json() == {"result": "<div>gpt</div>"}
    mock_analyze.assert_called_once_with("x = 1", "otomatik tespit", provider="chatgpt")


def test_upload_single_file():
    with patch("main.analyze_code", return_value="<div>single</div>") as mock_analyze:
        resp = client.post(
            "/upload",
            files={"file": ("app.py", b"print('hi')", "text/x-python")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "file"
    assert data["result"] == "<div>single</div>"
    mock_analyze.assert_called_once_with("print('hi')", "PY", provider="claude")


def test_upload_unsupported_extension():
    resp = client.post("/upload", files={"file": ("malware.exe", b"binary", "application/octet-stream")})
    assert resp.status_code == 200
    assert "error" in resp.json()


def test_upload_unconfigured_provider_returns_friendly_error_before_parsing():
    with patch("main.is_configured", return_value=False):
        resp = client.post(
            "/upload",
            files={"file": ("app.py", b"print('hi')", "text/x-python")},
            data={"provider": "gemini"},
        )
    assert resp.status_code == 200
    assert "yapılandırılmamış" in resp.json()["error"]


def test_upload_zip_multiple_small_files_analyzed_together():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("main.py", "print('a')")
        zf.writestr("utils.py", "print('b')")
    buf.seek(0)

    with patch("main.analyze_multi", return_value="<div>zip-result</div>") as mock_multi:
        resp = client.post("/upload", files={"file": ("project.zip", buf.getvalue(), "application/zip")})

    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "zip"
    assert len(data["results"]) == 2
    assert all(r["result"] == "<div>zip-result</div>" for r in data["results"])
    assert mock_multi.call_args.kwargs == {"provider": "claude"}
    assert len(mock_multi.call_args.args[0]) == 2


def test_github_invalid_url_returns_error_without_streaming():
    resp = client.post("/github", json={"url": "not-a-github-url"})
    assert resp.status_code == 200
    assert resp.json() == {"error": "Geçersiz GitHub URL'i."}


def test_github_unconfigured_provider_returns_error_without_streaming():
    with patch("main.is_configured", return_value=False):
        resp = client.post("/github", json={"url": "https://github.com/owner/repo", "provider": "gemini"})
    assert resp.status_code == 200
    assert "yapılandırılmamış" in resp.json()["error"]


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

    with patch("main.analyze_code", return_value="<div>found nothing</div>") as mock_analyze:
        resp = client.post("/github", json={"url": "https://github.com/owner/repo"})

    lines = [json.loads(l) for l in resp.text.strip().splitlines()]
    types = [l["type"] for l in lines]
    assert types[0] == "start"
    assert "progress" in types
    assert "result" in types
    assert types[-1] == "done"
    mock_analyze.assert_called_once_with("print('hello')", "PY", provider="claude")


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
