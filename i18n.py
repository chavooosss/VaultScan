from fastapi import Request

MESSAGES = {
    "tr": {
        "login_required": "Giriş yapmanız gerekiyor.",
        "rate_limited": "Çok fazla istek gönderdiniz. Lütfen bir dakika bekleyip tekrar deneyin.",
        "csrf_failed": "Güvenlik doğrulaması başarısız (CSRF). Sayfayı yenileyip tekrar deneyin.",
        "unknown_provider": "Bilinmeyen AI sağlayıcı: {provider}",
        "missing_api_key": "{label} için kendi API key'inizi eklemediniz. Ayarlar sayfasından ekleyebilirsiniz.",
        "select_at_least_one_provider": "En az bir AI seçmelisiniz.",
        "code_too_large": "Kod çok büyük (maks {max_len} karakter). Büyük dosyalar için dosya/zip yükleme sekmesini kullan.",
        "analysis_error": "Analiz hatası: {error}",
        "file_too_large": "Dosya çok büyük (maks {mb} MB).",
        "no_supported_files_in_zip": "Zip içinde desteklenen dosya bulunamadı.",
        "unsupported_file_format": "Desteklenmeyen dosya formatı: {ext}",
        "invalid_github_url": "Geçersiz GitHub URL'i.",
        "github_token_invalid": "GitHub token geçersiz veya süresi dolmuş.",
        "github_rate_limited": "GitHub API rate limit'e ulaşıldı. Birkaç dakika sonra tekrar deneyin veya bir token ekleyin.",
        "github_access_denied": "Bu repoya erişim izniniz yok.",
        "github_repo_not_found": "Repo bulunamadı: {owner}/{repo}. Private bir repoysa token girmeniz gerekebilir.",
        "github_api_error": "GitHub API hatası (HTTP {status}).",
        "no_supported_files_found": "Desteklenen dosya bulunamadı.",
        "no_files_downloaded": "Hiçbir dosya indirilemedi. Bağlantınızı kontrol edip tekrar deneyin.",
        "phase_downloading": "indiriliyor",
        "phase_analyzing_together": "birlikte analiz ediliyor",
        "phase_analyzing": "analiz ediliyor",
        "github_timeout": "GitHub'a bağlanırken zaman aşımı oluştu. Tekrar deneyin.",
        "connection_error": "Bağlantı hatası: {error}",
        "api_key_empty": "API key boş olamaz.",
        "record_not_found": "Kayıt bulunamadı.",
        "and_n_more_files": "+ {n} dosya",
    },
    "en": {
        "login_required": "You need to log in.",
        "rate_limited": "Too many requests. Please wait a minute and try again.",
        "csrf_failed": "Security check failed (CSRF). Please refresh the page and try again.",
        "unknown_provider": "Unknown AI provider: {provider}",
        "missing_api_key": "You haven't added your own API key for {label} yet. You can add it on the Settings page.",
        "select_at_least_one_provider": "You must select at least one AI.",
        "code_too_large": "Code is too large (max {max_len} characters). Use the file/zip upload tab for large files.",
        "analysis_error": "Analysis error: {error}",
        "file_too_large": "File is too large (max {mb} MB).",
        "no_supported_files_in_zip": "No supported files found in the zip.",
        "unsupported_file_format": "Unsupported file format: {ext}",
        "invalid_github_url": "Invalid GitHub URL.",
        "github_token_invalid": "GitHub token is invalid or expired.",
        "github_rate_limited": "GitHub API rate limit reached. Try again in a few minutes or add a token.",
        "github_access_denied": "You don't have access to this repo.",
        "github_repo_not_found": "Repo not found: {owner}/{repo}. If it's private, you may need to provide a token.",
        "github_api_error": "GitHub API error (HTTP {status}).",
        "no_supported_files_found": "No supported files found.",
        "no_files_downloaded": "No files could be downloaded. Check your connection and try again.",
        "phase_downloading": "downloading",
        "phase_analyzing_together": "analyzing together",
        "phase_analyzing": "analyzing",
        "github_timeout": "Timed out while connecting to GitHub. Please try again.",
        "connection_error": "Connection error: {error}",
        "api_key_empty": "API key cannot be empty.",
        "record_not_found": "Record not found.",
        "and_n_more_files": "+ {n} files",
    },
}

def get_lang(request: Request) -> str:
    lang = request.headers.get("x-lang", "tr").lower()
    return lang if lang in MESSAGES else "tr"

def t(lang: str, key: str, **kwargs) -> str:
    msg = MESSAGES.get(lang, MESSAGES["tr"]).get(key, key)
    return msg.format(**kwargs) if kwargs else msg
