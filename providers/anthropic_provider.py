import anthropic
from config import ANTHROPIC_API_KEY, MODEL, MAX_TOKENS
from prompts import SYSTEM_PROMPT
from providers.errors import ProviderNotConfigured

_client = None

def _get_client():
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            raise ProviderNotConfigured("Claude (Anthropic) için API key yapılandırılmamış.")
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client

def is_configured() -> bool:
    return bool(ANTHROPIC_API_KEY)

def analyze_code(code: str, language: str = "otomatik tespit") -> str:
    message = _get_client().messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Dil: {language}\n\nKod:\n```\n{code}\n```"
            }
        ]
    )
    return message.content[0].text

def analyze_multi(files: list) -> str:
    parts = [f"### {f['path']}\n```\n{f['code']}\n```" for f in files]
    content = "Aşağıdaki dosyalar birbiriyle ilişkili, birlikte analiz et:\n\n" + "\n\n".join(parts)
    message = _get_client().messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": content
            }
        ]
    )
    return message.content[0].text
