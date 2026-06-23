import anthropic
from config import MODEL, MAX_TOKENS
from prompts import SYSTEM_PROMPT, SYNTHESIS_PROMPT
from providers.errors import ProviderNotConfigured

def _client(api_key: str):
    if not api_key:
        raise ProviderNotConfigured("Claude (Anthropic) için API key girilmemiş.")
    return anthropic.Anthropic(api_key=api_key)

def analyze_code(code: str, language: str, api_key: str) -> str:
    message = _client(api_key).messages.create(
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

def analyze_multi(files: list, api_key: str) -> str:
    parts = [f"### {f['path']}\n```\n{f['code']}\n```" for f in files]
    content = "Aşağıdaki dosyalar birbiriyle ilişkili, birlikte analiz et:\n\n" + "\n\n".join(parts)
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
