from openai import OpenAI
from config import OPENAI_MODEL, MAX_TOKENS, PROVIDER_TIMEOUT_SECONDS
from prompts import get_system_prompt, get_synthesis_prompt, code_content, multi_intro, with_project_context
from providers.errors import ProviderNotConfigured

def _client(api_key: str):
    if not api_key:
        raise ProviderNotConfigured("ChatGPT (OpenAI) için API key girilmemiş.")
    return OpenAI(api_key=api_key, timeout=PROVIDER_TIMEOUT_SECONDS)

def analyze_code(code: str, language: str, api_key: str, project_context: str = "", lang: str = "tr") -> str:
    content = with_project_context(code_content(code, language, lang), project_context)
    response = _client(api_key).chat.completions.create(
        model=OPENAI_MODEL,
        max_completion_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": get_system_prompt(lang)},
            {"role": "user", "content": content}
        ]
    )
    return response.choices[0].message.content

def synthesize(content: str, api_key: str, lang: str = "tr") -> str:
    response = _client(api_key).chat.completions.create(
        model=OPENAI_MODEL,
        max_completion_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": get_synthesis_prompt(lang)},
            {"role": "user", "content": content}
        ]
    )
    return response.choices[0].message.content

def analyze_multi(files: list, api_key: str, project_context: str = "", lang: str = "tr") -> str:
    parts = [f"### {f['path']}\n```\n{f['code']}\n```" for f in files]
    content = with_project_context(
        multi_intro(lang) + "\n\n".join(parts),
        project_context,
    )
    response = _client(api_key).chat.completions.create(
        model=OPENAI_MODEL,
        max_completion_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": get_system_prompt(lang)},
            {"role": "user", "content": content}
        ]
    )
    return response.choices[0].message.content
