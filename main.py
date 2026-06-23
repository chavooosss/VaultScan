import zipfile
import io
import httpx
import re
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from analyzer import analyze_code_collab, analyze_multi_collab
from providers import PROVIDERS, PROVIDER_LABELS, DEFAULT_PROVIDER, is_configured
import json

app = FastAPI()

SUPPORTED_EXTENSIONS = {
    '.py', '.js', '.ts', '.php', '.java', '.go', '.rs',
    '.c', '.cpp', '.h', '.cs', '.rb', '.swift', '.kt',
    '.sql', '.html', '.css', '.sh', '.yaml', '.yml', '.json'
}

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
    MAX_GROUP_SIZE = 8000

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

class AnalyzeRequest(BaseModel):
    code: str
    language: str = "otomatik tespit"
    providers: list[str] = [DEFAULT_PROVIDER]

class GithubRequest(BaseModel):
    url: str
    token: str = ""
    max_files: int = 20
    providers: list[str] = [DEFAULT_PROVIDER]

def parse_github_url(url: str):
    url = url.strip().rstrip("/").replace(".git", "")
    pattern = r"github\.com/([^/]+)/([^/]+)"
    match = re.search(pattern, url)
    if not match:
        return None, None
    return match.group(1), match.group(2)

def validate_provider(provider: str) -> str | None:
    if provider not in PROVIDERS:
        return f"Bilinmeyen AI sağlayıcı: {provider}"
    if not is_configured(provider):
        label = PROVIDER_LABELS.get(provider, provider)
        return f"{label} için API key yapılandırılmamış. Lütfen başka bir AI seçin."
    return None

def validate_providers(providers: list[str]) -> str | None:
    if not providers:
        return "En az bir AI seçmelisiniz."
    for provider in providers:
        error = validate_provider(provider)
        if error:
            return error
    return None

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    error = validate_providers(request.providers)
    if error:
        return {"error": error}
    try:
        result = await analyze_code_collab(request.code, request.language, request.providers)
    except Exception as e:
        return {"error": f"Analiz hatası: {e}"}
    return {"result": result}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), providers: str = Form(DEFAULT_PROVIDER)):
    provider_list = [p.strip() for p in providers.split(",") if p.strip()]
    error = validate_providers(provider_list)
    if error:
        return {"error": error}

    filename = file.filename or ""
    content = await file.read()

    if filename.endswith(".zip"):
        file_contents = []
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            for name in zf.namelist():
                ext = "." + name.split(".")[-1].lower() if "." in name else ""
                if ext not in SUPPORTED_EXTENSIONS:
                    continue
                if 'node_modules' in name or 'vendor' in name or '.min.' in name:
                    continue
                try:
                    code = zf.read(name).decode("utf-8", errors="ignore")
                    if not code.strip():
                        continue
                    file_contents.append({"path": name, "code": code, "language": name.split(".")[-1].upper()})
                except Exception:
                    continue

        file_contents.sort(key=lambda f: score_file(f['path']), reverse=True)
        file_contents = file_contents[:20]

        groups = group_files_by_context(file_contents)
        results = []
        for group in groups:
            is_multi = len(group) > 1
            try:
                if is_multi:
                    result = await analyze_multi_collab(group, provider_list)
                else:
                    result = await analyze_code_collab(group[0]['code'], group[0]['language'], provider_list)
            except Exception as e:
                result = f"<p class=\"error-text\">Analiz hatası: {e}</p>"

            if is_multi:
                for item in group:
                    results.append({"file": item['path'], "result": result})
                break
            else:
                results.append({"file": group[0]['path'], "result": result})

        return {"type": "zip", "results": results}

    ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_EXTENSIONS:
        return {"error": f"Desteklenmeyen dosya formatı: {ext}"}

    code = content.decode("utf-8", errors="ignore")
    language = filename.split(".")[-1].upper() if "." in filename else "otomatik tespit"
    try:
        result = await analyze_code_collab(code, language, provider_list)
    except Exception as e:
        return {"error": f"Analiz hatası: {e}"}
    return {"type": "file", "result": result}

@app.post("/github")
async def analyze_github(request: GithubRequest):
    owner, repo = parse_github_url(request.url)
    if not owner or not repo:
        return {"error": "Geçersiz GitHub URL'i."}

    provider_error = validate_providers(request.providers)
    if provider_error:
        return {"error": provider_error}

    headers = {"Accept": "application/vnd.github.v3+json"}
    if request.token:
        headers["Authorization"] = f"token {request.token}"

    def github_error_message(resp) -> str:
        if resp.status_code == 401:
            return "GitHub token geçersiz veya süresi dolmuş."
        if resp.status_code == 403:
            if resp.headers.get("X-RateLimit-Remaining") == "0":
                return "GitHub API rate limit'e ulaşıldı. Birkaç dakika sonra tekrar deneyin veya bir token ekleyin."
            return "Bu repoya erişim izniniz yok."
        if resp.status_code == 404:
            return f"Repo bulunamadı: {owner}/{repo}. Private bir repoysa token girmeniz gerekebilir."
        return f"GitHub API hatası (HTTP {resp.status_code})."

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
                files = files[:request.max_files]

                if not files:
                    yield json.dumps({"type": "error", "message": "Desteklenen dosya bulunamadı."}) + "\n"
                    return

                total = len(files)
                yield json.dumps({"type": "start", "total": total, "repo": f"{owner}/{repo}"}) + "\n"

                file_contents = []
                for i, f in enumerate(files):
                    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{f['path']}"
                    yield json.dumps({"type": "progress", "current": i + 1, "total": total, "file": f["path"], "phase": "indiriliyor"}) + "\n"
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
                    yield json.dumps({"type": "error", "message": "Hiçbir dosya indirilemedi. Bağlantınızı kontrol edip tekrar deneyin."}) + "\n"
                    return

                groups = group_files_by_context(file_contents)
                analyzed = 0

                for group in groups:
                    is_multi = len(group) > 1
                    label = f"📦 {group[0]['path']} + {len(group)-1} dosya" if is_multi else group[0]["path"]
                    phase = "birlikte analiz ediliyor" if is_multi else "analiz ediliyor"
                    progress_file = ", ".join(g["path"] for g in group) if is_multi else group[0]["path"]

                    yield json.dumps({"type": "progress", "current": analyzed + 1, "total": len(file_contents), "file": progress_file, "phase": phase}) + "\n"
                    try:
                        if is_multi:
                            result = await analyze_multi_collab(group, request.providers)
                        else:
                            result = await analyze_code_collab(group[0]["code"], group[0]["language"], request.providers)
                    except Exception as e:
                        result = f"<p class=\"error-text\">Analiz hatası: {e}</p>"
                    yield json.dumps({"type": "result", "file": label, "result": result}) + "\n"
                    analyzed += len(group)

                yield json.dumps({"type": "done"}) + "\n"
        except httpx.TimeoutException:
            yield json.dumps({"type": "error", "message": "GitHub'a bağlanırken zaman aşımı oluştu. Tekrar deneyin."}) + "\n"
        except httpx.RequestError as e:
            yield json.dumps({"type": "error", "message": f"Bağlantı hatası: {e}"}) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

app.mount("/static", StaticFiles(directory="static"), name="static")