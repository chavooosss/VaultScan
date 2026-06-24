import anthropic
from config import MODEL, MAX_TOKENS, PROVIDER_TIMEOUT_SECONDS
from prompts import SYSTEM_PROMPT, SYNTHESIS_PROMPT, with_project_context
from providers.errors import ProviderNotConfigured

def _client(api_key: str):
    if not api_key:
        raise ProviderNotConfigured("Claude (Anthropic) için API key girilmemiş.")
    return anthropic.Anthropic(api_key=api_key, timeout=PROVIDER_TIMEOUT_SECONDS)

def analyze_code(code: str, language: str, api_key: str, project_context: str = "") -> str:
    content = with_project_context(f"Dil: {language}\n\nKod:\n```\n{code}\n```", project_context)
    message = _client(api_key).messages.create(
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

def synthesize(content: str, api_key: str) -> str:
    message = _client(api_key).messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYNTHESIS_PROMPT,
        messages=[
            {
                "role": "user",
                "content": content
            }
        ]
    )
    return message.content[0].text

def analyze_multi(files: list, api_key: str, project_context: str = "") -> str:
    parts = [f"### {f['path']}\n```\n{f['code']}\n```" for f in files]
    content = with_project_context(
        "Aşağıdaki dosyalar birbiriyle ilişkili, birlikte analiz et:\n\n" + "\n\n".join(parts),
        project_context,
    )
    message = _client(api_key).messages.create(
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
