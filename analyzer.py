from providers import get_provider, DEFAULT_PROVIDER

def analyze_code(code: str, language: str = "otomatik tespit", provider: str = DEFAULT_PROVIDER) -> str:
    return get_provider(provider).analyze_code(code, language)

def analyze_multi(files: list, provider: str = DEFAULT_PROVIDER) -> str:
    return get_provider(provider).analyze_multi(files)
