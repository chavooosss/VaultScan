import asyncio
import logging
import os
import zipfile
import html
import io
import httpx
import re
import secrets
import time
import threading
from collections import defaultdict, deque
from fastapi import FastAPI, UploadFile, File, Form, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from analyzer import analyze_code_collab, analyze_multi_collab
from providers import PROVIDERS, PROVIDER_LABELS, DEFAULT_PROVIDER
from authlib.integrations.base_client.errors import OAuthError
from auth import oauth
from db import (
    init_db, get_db, get_or_create_user, get_user_api_key, set_user_api_key, clear_user_api_key, User,
    save_analysis, get_user_history, get_analysis_by_id, delete_analysis, set_history_enabled,
    severity_counts_str,
)
from config import SESSION_SECRET
from i18n import t, get_lang
import json

logger = logging.getLogger("vaultscan")

_IS_PRODUCTION = bool(os.getenv("RENDER"))

app = FastAPI(
    docs_url=None if _IS_PRODUCTION else "/docs",
    redoc_url=None if _IS_PRODUCTION else "/redoc",
    openapi_url=None if _IS_PRODUCTION else "/openapi.json",
)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, https_only=_IS_PRODUCTION)
init_db()

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    if not request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store"
    return response

SUPPORTED_EXTENSIONS = {
    '.py', '.js', '.ts', '.php', '.java', '.go', '.rs',
    '.c', '.cpp', '.h', '.cs', '.rb', '.swift', '.kt',
    '.sql', '.html', '.css', '.sh', '.yaml', '.yml', '.json'
}

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_ZIP_ENTRY_SIZE = 2 * 1024 * 1024  # 2 MB (zip bomb koruması)
MAX_PASTE_LENGTH = 200_000  # karakter — /analyze'a sınırsız boyutta metin gönderilmesini engeller
MAX_GITHUB_FILES = 50
MAX_PROJECT_TREE_CHARS = 3000

ANALYSIS_RATE_LIMIT = 10  # her route için kullanıcı bazlı, pencere başına
ANALYSIS_RATE_WINDOW_SECONDS = 60

_rate_limit_buckets: dict[str, deque] = defaultdict(deque)
_rate_limit_lock = threading.Lock()

def check_rate_limit(key: str, max_requests: int = ANALYSIS_RATE_LIMIT, window_seconds: int = ANALYSIS_RATE_WINDOW_SECONDS) -> bool:
    now = time.monotonic()
    with _rate_limit_lock:
        bucket = _rate_limit_buckets[key]
        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()
        if len(bucket) >= max_requests:
            return False
        bucket.append(now)
        return True

def rate_limit_error(http_request: Request, route_name: str, lang: str = "tr") -> str | None:
    user_id = http_request.session.get("user_id")
    key = f"{route_name}:user:{user_id}" if user_id else f"{route_name}:ip:{http_request.client.host}"
    if not check_rate_limit(key):
        return t(lang, "rate_limited")
    return None

# Kritik dosya isimleri — önce bunlar analiz edilir
PRIORITY_PATTERNS = [
    'main', 'app', 'index', 'server', 'auth', 'login', 'config',
    'settings', 'database', 'db', 'models', 'api', 'routes',
    'middleware', 'admin', 'user', 'password', 'secret', 'key',
    'token', 'payment', 'upload', 'security'
]

def score_file(path: str) -> int:
    name = path.lower().split('/')[-1].split('.')[0]
    score = 0
    for pattern in PRIORITY_PATTERNS:
        if pattern in name:
            score += 10
    if any(path.endswith(ext) for ext in ['.py', '.js', '.ts', '.php', '.java']):
        score += 5
    if 'test' in path.lower() or 'spec' in path.lower():
        score -= 20
    if 'node_modules' in path or 'vendor' in path or '.min.' in path:
        score -= 50
    return score

def group_files_by_context(files: list) -> list[list]:
    groups = []
    current_group = []
    current_size = 0
    MAX_GROUP_SIZE = 30000

    for f in files:
        size = f.get('size', 0)
        if current_size + size > MAX_GROUP_SIZE and current_group:
            groups.append(current_group)
            current_group = [f]
            current_size = size
        else:
            current_group.append(f)
            current_size += size

    if current_group:
        groups.append(current_group)

    return groups

def build_project_context(repo_label: str, paths: list[str], lang: str = "tr") -> str:
    tree = "\n".join(paths)
    if lang == "en":
        if len(tree) > MAX_PROJECT_TREE_CHARS:
            truncated = tree[:MAX_PROJECT_TREE_CHARS]
            tree = truncated.rsplit("\n", 1)[0] + "\n... (rest truncated)"
        return (
            f"[Project structure — {repo_label}]\n"
            f"Relevant files in this repo:\n{tree}\n\n"
            "The file(s) below are part of this project. When analyzing, don't just look "
            "at this piece in isolation — also consider the project's overall structure; "
            "for example, try to infer from the file names how a function/input you see "
            "here might be called from other files, and what the project's purpose is."
        )
    if len(tree) > MAX_PROJECT_TREE_CHARS:
        truncated = tree[:MAX_PROJECT_TREE_CHARS]
        tree = truncated.rsplit("\n", 1)[0] + "\n... (devamı kısaltıldı)"
    return (
        f"[Proje yapısı — {repo_label}]\n"
        f"Bu depodaki ilgili dosyalar:\n{tree}\n\n"
        "Aşağıdaki dosya/dosyalar bu projenin bir parçası. Analiz ederken sadece bu "
        "parçaya değil, projenin genel yapısına da bak; örneğin burada gördüğün bir "
        "fonksiyon/girdinin başka dosyalarda nasıl çağrılabileceğini, projenin "
        "amacını dosya adlarından çıkarmaya çalış."
    )

HEARTBEAT_INTERVAL_SECONDS = 8

async def run_with_heartbeat(coro):
    """coro'yu bekler, beklerken periyodik olarak ("ping", None) üretir.

    AI çağrıları uzun sürebiliyor (90s'e kadar); aradan hiç byte göndermeden
    tek seferlik bir yanıt beklemek, Render gibi reverse proxy'lerin boşta
    kalan bağlantıyı zaman aşımına uğratmasına yol açıyordu — istemci hata
    görse de sunucu işi arka planda bitirip token harcamaya devam ediyordu.
    Periyodik ping byte'ları bağlantıyı canlı tutar.
    """
    task = asyncio.ensure_future(coro)
    while True:
        done, _ = await asyncio.wait({task}, timeout=HEARTBEAT_INTERVAL_SECONDS)
        if task in done:
            yield ("done", task.result())
            return
        yield ("ping", None)

def combine_results_html(results: list[dict]) -> str:
    return "".join(
        f'<div class="file-section"><div class="file-name">📄 {html.escape(r["file"])}</div>{r["result"]}</div>'
        for r in results
    )

def parse_severity_counts(stored: str) -> dict:
    try:
        critical, high, medium, low = (int(x) for x in stored.split(","))
    except (ValueError, AttributeError):
        critical, high, medium, low = 0, 0, 0, 0
    return {"critical": critical, "high": high, "medium": medium, "low": low}

class AnalyzeRequest(BaseModel):
    code: str
    language: str = "otomatik tespit"
    providers: list[str] = [DEFAULT_PROVIDER]

class GithubRequest(BaseModel):
    url: str
    token: str = ""
    max_files: int = 20
    providers: list[str] = [DEFAULT_PROVIDER]

class ApiKeyRequest(BaseModel):
    provider: str
    api_key: str

class HistoryToggleRequest(BaseModel):
    enabled: bool

def parse_github_url(url: str):
    url = url.strip().rstrip("/").replace(".git", "")
    pattern = r"github\.com/([^/]+)/([^/]+)"
    match = re.search(pattern, url)
    if not match:
        return None, None
    return match.group(1), match.group(2)

def get_current_user(http_request: Request, db: Session) -> User | None:
    user_id = http_request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)

def get_or_create_csrf_token(http_request: Request) -> str:
    token = http_request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        http_request.session["csrf_token"] = token
    return token

def verify_csrf(http_request: Request, lang: str = "tr") -> str | None:
    session_token = http_request.session.get("csrf_token")
    header_token = http_request.headers.get("x-csrf-token", "")
    if not session_token or not secrets.compare_digest(session_token, header_token):
        return t(lang, "csrf_failed")
    return None

def validate_provider(provider: str, user: User, lang: str = "tr") -> str | None:
    if provider not in PROVIDERS:
        return t(lang, "unknown_provider", provider=provider)
    if not get_user_api_key(user, provider):
        label = PROVIDER_LABELS.get(provider, provider)
        return t(lang, "missing_api_key", label=label)
    return None

def validate_providers(providers: list[str], user: User, lang: str = "tr") -> str | None:
    if not providers:
        return t(lang, "select_at_least_one_provider")
    for provider in providers:
        error = validate_provider(provider, user, lang)
        if error:
            return error
    return None

def build_api_keys(providers: list[str], user: User) -> dict:
    return {p: get_user_api_key(user, p) for p in providers}

@app.post("/analyze")
async def analyze(request: AnalyzeRequest, http_request: Request, db: Session = Depends(get_db)):
    lang = get_lang(http_request)
    user = get_current_user(http_request, db)
    if user is None:
        return {"error": t(lang, "login_required")}
    rate_error = rate_limit_error(http_request, "analyze", lang)
    if rate_error:
        return {"error": rate_error}
    csrf_error = verify_csrf(http_request, lang)
    if csrf_error:
        return {"error": csrf_error}
    if len(request.code) > MAX_PASTE_LENGTH:
        return {"error": t(lang, "code_too_large", max_len=f"{MAX_PASTE_LENGTH:,}")}
    error = validate_providers(request.providers, user, lang)
    if error:
        return {"error": error}
    api_keys = build_api_keys(request.providers, user)

    async def stream():
        try:
            result = None
            async for kind, payload in run_with_heartbeat(
                analyze_code_collab(request.code, request.language, request.providers, api_keys, lang=lang)
            ):
                if kind == "ping":
                    yield json.dumps({"type": "ping"}) + "\n"
                else:
                    result = payload
        except Exception as e:
            yield json.dumps({"type": "error", "message": t(lang, "analysis_error", error=e)}) + "\n"
            return
        source_label = "Pasted code" if lang == "en" else "Yapıştırılan kod"
        if user.history_enabled:
            save_analysis(db, user, request.providers, "paste", source_label, result, severity_counts_str(result))
        yield json.dumps({"type": "result", "result": result}) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")

@app.post("/upload")
async def upload_file(http_request: Request, file: UploadFile = File(...), providers: str = Form(DEFAULT_PROVIDER), db: Session = Depends(get_db)):
    lang = get_lang(http_request)
    user = get_current_user(http_request, db)
    if user is None:
        return {"error": t(lang, "login_required")}
    rate_error = rate_limit_error(http_request, "upload", lang)
    if rate_error:
        return {"error": rate_error}
    csrf_error = verify_csrf(http_request, lang)
    if csrf_error:
        return {"error": csrf_error}
    provider_list = [p.strip() for p in providers.split(",") if p.strip()]
    error = validate_providers(provider_list, user, lang)
    if error:
        return {"error": error}
    api_keys = build_api_keys(provider_list, user)

    filename = file.filename or ""
    content = await file.read()

    if len(content) > MAX_UPLOAD_SIZE:
        return {"error": t(lang, "file_too_large", mb=MAX_UPLOAD_SIZE // (1024*1024))}

    is_zip = filename.endswith(".zip")

    if is_zip:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            candidates = []
            for info in zf.infolist():
                name = info.filename
                ext = "." + name.split(".")[-1].lower() if "." in name else ""
                if ext not in SUPPORTED_EXTENSIONS:
                    continue
                if 'node_modules' in name or 'vendor' in name or '.min.' in name:
                    continue
                if info.file_size > MAX_ZIP_ENTRY_SIZE:
                    continue
                candidates.append(info)

            # Hangi 20 dosyanın açılacağına, hiçbirini decompress etmeden önce karar ver
            # (zip bomb koruması — çok girişli bir zip'in hepsini belleğe açıp sonra
            # çoğunu çöpe atmak yerine, sadece seçilenleri açıyoruz).
            candidates.sort(key=lambda info: score_file(info.filename), reverse=True)
            candidates = candidates[:20]

            file_contents = []
            for info in candidates:
                try:
                    code = zf.read(info.filename).decode("utf-8", errors="ignore")
                    if not code.strip():
                        continue
                    file_contents.append({"path": info.filename, "code": code, "language": info.filename.split(".")[-1].upper(), "size": len(code)})
                except Exception:
                    continue

        if not file_contents:
            return {"error": t(lang, "no_supported_files_in_zip")}
    else:
        ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
        if ext not in SUPPORTED_EXTENSIONS:
            return {"error": t(lang, "unsupported_file_format", ext=ext)}
        code = content.decode("utf-8", errors="ignore")
        language = filename.split(".")[-1].upper() if "." in filename else "otomatik tespit"
        file_contents = [{"path": filename, "code": code, "language": language, "size": len(code)}]

    groups = group_files_by_context(file_contents)

    async def stream():
        results = []
        for group in groups:
            is_multi = len(group) > 1
            try:
                coro = (
                    analyze_multi_collab(group, provider_list, api_keys, lang=lang) if is_multi
                    else analyze_code_collab(group[0]['code'], group[0]['language'], provider_list, api_keys, lang=lang)
                )
                result = None
                async for kind, payload in run_with_heartbeat(coro):
                    if kind == "ping":
                        yield json.dumps({"type": "ping"}) + "\n"
                    else:
                        result = payload
            except Exception as e:
                result = f"<p class=\"error-text\">{t(lang, 'analysis_error', error=e)}</p>"

            if is_multi:
                for item in group:
                    results.append({"file": item['path'], "result": result})
            else:
                results.append({"file": group[0]['path'], "result": result})

        if user.history_enabled:
            history_html = combine_results_html(results) if is_zip else results[0]["result"]
            save_analysis(db, user, provider_list, "file", filename, history_html, severity_counts_str(history_html))

        if is_zip:
            yield json.dumps({"type": "result", "result_type": "zip", "results": results}) + "\n"
        else:
            yield json.dumps({"type": "result", "result_type": "file", "result": results[0]["result"]}) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")

@app.post("/github")
async def analyze_github(request: GithubRequest, http_request: Request, db: Session = Depends(get_db)):
    lang = get_lang(http_request)
    user = get_current_user(http_request, db)
    if user is None:
        return {"error": t(lang, "login_required")}
    rate_error = rate_limit_error(http_request, "github", lang)
    if rate_error:
        return {"error": rate_error}
    csrf_error = verify_csrf(http_request, lang)
    if csrf_error:
        return {"error": csrf_error}
    owner, repo = parse_github_url(request.url)
    if not owner or not repo:
        return {"error": t(lang, "invalid_github_url")}

    provider_error = validate_providers(request.providers, user, lang)
    if provider_error:
        return {"error": provider_error}

    api_keys = build_api_keys(request.providers, user)

    headers = {"Accept": "application/vnd.github.v3+json"}
    if request.token:
        headers["Authorization"] = f"token {request.token}"

    def github_error_message(resp) -> str:
        if resp.status_code == 401:
            return t(lang, "github_token_invalid")
        if resp.status_code == 403:
            if resp.headers.get("X-RateLimit-Remaining") == "0":
                return t(lang, "github_rate_limited")
            return t(lang, "github_access_denied")
        if resp.status_code == 404:
            return t(lang, "github_repo_not_found", owner=owner, repo=repo)
        return t(lang, "github_api_error", status=resp.status_code)

    async def stream():
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
                tree_resp = await client.get(tree_url, headers=headers)
                if tree_resp.status_code != 200:
                    yield json.dumps({"type": "error", "message": github_error_message(tree_resp)}) + "\n"
                    return

                tree = tree_resp.json().get("tree", [])
                files = [
                    f for f in tree
                    if f["type"] == "blob" and
                    any(f["path"].endswith(ext) for ext in SUPPORTED_EXTENSIONS) and
                    f.get("size", 0) < 100000 and
                    'node_modules' not in f["path"] and
                    'vendor' not in f["path"] and
                    '.min.' not in f["path"]
                ]

                files.sort(key=lambda f: score_file(f["path"]), reverse=True)
                files = files[:max(1, min(request.max_files, MAX_GITHUB_FILES))]
                project_context = build_project_context(f"{owner}/{repo}", [f["path"] for f in files], lang)

                if not files:
                    yield json.dumps({"type": "error", "message": t(lang, "no_supported_files_found")}) + "\n"
                    return

                total = len(files)
                yield json.dumps({"type": "start", "total": total, "repo": f"{owner}/{repo}"}) + "\n"

                file_contents = []
                for i, f in enumerate(files):
                    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{f['path']}"
                    yield json.dumps({"type": "progress", "current": i + 1, "total": total, "file": f["path"], "phase": t(lang, "phase_downloading")}) + "\n"
                    try:
                        resp = await client.get(raw_url, headers=headers)
                        if resp.status_code == 200:
                            file_contents.append({
                                "path": f["path"],
                                "code": resp.text,
                                "language": f["path"].split(".")[-1].upper(),
                                "size": len(resp.text)
                            })
                    except httpx.RequestError:
                        continue

                if not file_contents:
                    yield json.dumps({"type": "error", "message": t(lang, "no_files_downloaded")}) + "\n"
                    return

                groups = group_files_by_context(file_contents)
                analyzed = 0
                history_results = []

                for group in groups:
                    is_multi = len(group) > 1
                    label = f"📦 {group[0]['path']} {t(lang, 'and_n_more_files', n=len(group)-1)}" if is_multi else group[0]["path"]
                    phase = t(lang, "phase_analyzing_together") if is_multi else t(lang, "phase_analyzing")
                    progress_file = ", ".join(g["path"] for g in group) if is_multi else group[0]["path"]

                    yield json.dumps({"type": "progress", "current": analyzed + 1, "total": len(file_contents), "file": progress_file, "phase": phase}) + "\n"
                    try:
                        coro = (
                            analyze_multi_collab(group, request.providers, api_keys, project_context, lang=lang) if is_multi
                            else analyze_code_collab(group[0]["code"], group[0]["language"], request.providers, api_keys, project_context, lang=lang)
                        )
                        result = None
                        async for kind, payload in run_with_heartbeat(coro):
                            if kind == "ping":
                                yield json.dumps({"type": "ping"}) + "\n"
                            else:
                                result = payload
                    except Exception as e:
                        result = f"<p class=\"error-text\">{t(lang, 'analysis_error', error=e)}</p>"
                    yield json.dumps({"type": "result", "file": label, "result": result}) + "\n"
                    history_results.append({"file": label, "result": result})
                    analyzed += len(group)

                if user.history_enabled and history_results:
                    github_history_html = combine_results_html(history_results)
                    save_analysis(db, user, request.providers, "github", f"{owner}/{repo}", github_history_html, severity_counts_str(github_history_html))

                yield json.dumps({"type": "done"}) + "\n"
        except httpx.TimeoutException:
            yield json.dumps({"type": "error", "message": t(lang, "github_timeout")}) + "\n"
        except httpx.RequestError as e:
            yield json.dumps({"type": "error", "message": t(lang, "connection_error", error=e)}) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")

@app.get("/auth/google/login")
async def google_login(request: Request):
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError:
        logger.exception("Google OAuth callback başarısız oldu")
        return RedirectResponse(url="/?login_error=1")
    userinfo = token.get("userinfo") or await oauth.google.userinfo(token=token)
    user = get_or_create_user(
        db,
        google_id=userinfo["sub"],
        email=userinfo["email"],
        name=userinfo.get("name", ""),
        picture=userinfo.get("picture", ""),
    )
    request.session["user_id"] = user.id
    request.session["user_name"] = user.name
    request.session["user_picture"] = user.picture
    return RedirectResponse(url="/")

@app.get("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")

@app.get("/api/me")
async def me(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return {"authenticated": False}
    user = db.get(User, request.session["user_id"])
    if user is None:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "name": request.session.get("user_name", ""),
        "picture": request.session.get("user_picture", ""),
        "csrf_token": get_or_create_csrf_token(request),
    }

@app.get("/api/keys")
async def get_keys(request: Request, db: Session = Depends(get_db)):
    lang = get_lang(request)
    user = get_current_user(request, db)
    if user is None:
        return {"error": t(lang, "login_required")}
    return {p: bool(get_user_api_key(user, p)) for p in PROVIDERS}

@app.post("/api/keys")
async def save_key(request: ApiKeyRequest, http_request: Request, db: Session = Depends(get_db)):
    lang = get_lang(http_request)
    user = get_current_user(http_request, db)
    if user is None:
        return {"error": t(lang, "login_required")}
    csrf_error = verify_csrf(http_request, lang)
    if csrf_error:
        return {"error": csrf_error}
    if request.provider not in PROVIDERS:
        return {"error": t(lang, "unknown_provider", provider=request.provider)}
    if not request.api_key.strip():
        return {"error": t(lang, "api_key_empty")}
    set_user_api_key(db, user, request.provider, request.api_key.strip())
    return {"ok": True}

@app.delete("/api/keys/{provider}")
async def delete_key(provider: str, request: Request, db: Session = Depends(get_db)):
    lang = get_lang(request)
    user = get_current_user(request, db)
    if user is None:
        return {"error": t(lang, "login_required")}
    csrf_error = verify_csrf(request, lang)
    if csrf_error:
        return {"error": csrf_error}
    if provider not in PROVIDERS:
        return {"error": t(lang, "unknown_provider", provider=provider)}
    clear_user_api_key(db, user, provider)
    return {"ok": True}

@app.get("/api/history")
async def list_history(request: Request, db: Session = Depends(get_db)):
    lang = get_lang(request)
    user = get_current_user(request, db)
    if user is None:
        return {"error": t(lang, "login_required")}
    history = get_user_history(db, user)
    return {
        "history_enabled": user.history_enabled,
        "items": [
            {
                "id": a.id,
                "created_at": a.created_at.isoformat(),
                "providers": a.providers.split(","),
                "source_type": a.source_type,
                "source_label": a.source_label,
                "severity_counts": parse_severity_counts(a.severity_counts),
            }
            for a in history
        ],
    }

@app.post("/api/history/toggle")
async def toggle_history(request: HistoryToggleRequest, http_request: Request, db: Session = Depends(get_db)):
    lang = get_lang(http_request)
    user = get_current_user(http_request, db)
    if user is None:
        return {"error": t(lang, "login_required")}
    csrf_error = verify_csrf(http_request, lang)
    if csrf_error:
        return {"error": csrf_error}
    set_history_enabled(db, user, request.enabled)
    return {"ok": True, "history_enabled": user.history_enabled}

@app.get("/api/history/{analysis_id}")
async def get_history_item(analysis_id: int, request: Request, db: Session = Depends(get_db)):
    lang = get_lang(request)
    user = get_current_user(request, db)
    if user is None:
        return {"error": t(lang, "login_required")}
    analysis = get_analysis_by_id(db, user, analysis_id)
    if analysis is None:
        return {"error": t(lang, "record_not_found")}
    return {
        "id": analysis.id,
        "created_at": analysis.created_at.isoformat(),
        "providers": analysis.providers.split(","),
        "source_type": analysis.source_type,
        "source_label": analysis.source_label,
        "result": analysis.result_html,
    }

@app.delete("/api/history/{analysis_id}")
async def delete_history_item(analysis_id: int, request: Request, db: Session = Depends(get_db)):
    lang = get_lang(request)
    user = get_current_user(request, db)
    if user is None:
        return {"error": t(lang, "login_required")}
    csrf_error = verify_csrf(request, lang)
    if csrf_error:
        return {"error": csrf_error}
    if not delete_analysis(db, user, analysis_id):
        return {"error": t(lang, "record_not_found")}
    return {"ok": True}

@app.get("/")
async def root(request: Request):
    if not request.session.get("user_id"):
        return FileResponse("static/login.html")
    return FileResponse("static/index.html")

@app.get("/settings")
async def settings_page(request: Request):
    if not request.session.get("user_id"):
        return FileResponse("static/login.html")
    return FileResponse("static/settings.html")

@app.get("/gizlilik")
async def privacy_page():
    return FileResponse("static/privacy.html")

@app.get("/demo")
async def demo_page():
    return FileResponse("static/demo.html")

@app.get("/robots.txt")
async def robots_txt():
    return FileResponse("static/robots.txt", media_type="text/plain")

@app.get("/history")
async def history_page(request: Request):
    if not request.session.get("user_id"):
        return FileResponse("static/login.html")
    return FileResponse("static/history.html")

app.mount("/static", StaticFiles(directory="static"), name="static")