from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL, MAX_TOKENS
from prompts import SYSTEM_PROMPT, SYNTHESIS_PROMPT
from providers.errors import ProviderNotConfigured

_client = None

def _get_client():
    global _client
    if _client is None:
        if not OPENAI_API_KEY:
            raise ProviderNotConfigured("ChatGPT (OpenAI) için API key yapılandırılmamış.")
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client

def is_configured() -> bool:
    return bool(OPENAI_API_KEY)

def analyze_code(code: str, language: str = "otomatik tespit") -> str:
    response = _get_client().chat.completions.create(
        model=OPENAI_MODEL,
        max_completion_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Dil: {language}\n\nKod:\n```\n{code}\n```"}
        ]
    )
    return response.choices[0].message.content

def synthesize(content: str) -> str:
    response = _get_client().chat.completions.create(
        model=OPENAI_MODEL,
        max_completion_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYNTHESIS_PROMPT},
            {"role": "user", "content": content}
        ]
    )
    return response.choices[0].message.content

def analyze_multi(files: list) -> str:
    parts = [f"### {f['path']}\n```\n{f['code']}\n```" for f in files]
    content = "Aşağıdaki dosyalar birbiriyle ilişkili, birlikte analiz et:\n\n" + "\n\n".join(parts)
    response = _get_client().chat.completions.create(
        model=OPENAI_MODEL,
        max_completion_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content}
        ]
    )
    return response.choices[0].message.content
