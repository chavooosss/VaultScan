import anthropic
from config import MODEL, MAX_TOKENS, PROVIDER_TIMEOUT_SECONDS
from prompts import get_system_prompt, get_synthesis_prompt, code_content, multi_intro, with_project_context
from providers.errors import ProviderNotConfigured

def _client(api_key: str):
    if not api_key:
        raise ProviderNotConfigured("Claude (Anthropic) için API key girilmemiş.")
    return anthropic.Anthropic(api_key=api_key, timeout=PROVIDER_TIMEOUT_SECONDS)

def analyze_code(code: str, language: str, api_key: str, project_context: str = "", lang: str = "tr") -> str:
    content = with_project_context(code_content(code, language, lang), project_context)
    message = _client(api_key).messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=get_system_prompt(lang),
        messages=[
            {
                "role": "user",
                "content": content
            }
        ]
    )
    return message.content[0].text

def synthesize(content: str, api_key: str, lang: str = "tr") -> str:
    message = _client(api_key).messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=get_synthesis_prompt(lang),
        messages=[
            {
                "role": "user",
                "content": content
            }
        ]
    )
    return message.content[0].text

def analyze_multi(files: list, api_key: str, project_context: str = "", lang: str = "tr") -> str:
    parts = [f"### {f['path']}\n```\n{f['code']}\n```" for f in files]
    content = with_project_context(
        multi_intro(lang) + "\n\n".join(parts),
        project_context,
    )
    message = _client(api_key).messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=get_system_prompt(lang),
        messages=[
            {
                "role": "user",
                "content": content
            }
        ]
    )
    return message.content[0].text
