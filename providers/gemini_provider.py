from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL, MAX_TOKENS
from prompts import SYSTEM_PROMPT
from providers.errors import ProviderNotConfigured

_client = None

def _get_client():
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise ProviderNotConfigured("Gemini (Google) için API key yapılandırılmamış.")
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client

def is_configured() -> bool:
    return bool(GEMINI_API_KEY)

def _config():
    return types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        max_output_tokens=MAX_TOKENS,
    )

def analyze_code(code: str, language: str = "otomatik tespit") -> str:
    response = _get_client().models.generate_content(
        model=GEMINI_MODEL,
        contents=f"Dil: {language}\n\nKod:\n```\n{code}\n```",
        config=_config(),
    )
    return response.text

def analyze_multi(files: list) -> str:
    parts = [f"### {f['path']}\n```\n{f['code']}\n```" for f in files]
    content = "Aşağıdaki dosyalar birbiriyle ilişkili, birlikte analiz et:\n\n" + "\n\n".join(parts)
    response = _get_client().models.generate_content(
        model=GEMINI_MODEL,
        contents=content,
        config=_config(),
    )
    return response.text
