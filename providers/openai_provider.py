from openai import OpenAI
from config import OPENAI_MODEL, MAX_TOKENS, PROVIDER_TIMEOUT_SECONDS
from prompts import SYSTEM_PROMPT, SYNTHESIS_PROMPT, with_project_context
from providers.errors import ProviderNotConfigured

def _client(api_key: str):
    if not api_key:
        raise ProviderNotConfigured("ChatGPT (OpenAI) için API key girilmemiş.")
    return OpenAI(api_key=api_key, timeout=PROVIDER_TIMEOUT_SECONDS)

def analyze_code(code: str, language: str, api_key: str, project_context: str = "") -> str:
    content = with_project_context(f"Dil: {language}\n\nKod:\n```\n{code}\n```", project_context)
    response = _client(api_key).chat.completions.create(
        model=OPENAI_MODEL,
        max_completion_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content}
        ]
    )
    return response.choices[0].message.content

def synthesize(content: str, api_key: str) -> str:
    response = _client(api_key).chat.completions.create(
        model=OPENAI_MODEL,
        max_completion_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYNTHESIS_PROMPT},
            {"role": "user", "content": content}
        ]
    )
    return response.choices[0].message.content

def analyze_multi(files: list, api_key: str, project_context: str = "") -> str:
    parts = [f"### {f['path']}\n```\n{f['code']}\n```" for f in files]
    content = with_project_context(
        "Aşağıdaki dosyalar birbiriyle ilişkili, birlikte analiz et:\n\n" + "\n\n".join(parts),
        project_context,
    )
    response = _client(api_key).chat.completions.create(
        model=OPENAI_MODEL,
        max_completion_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content}
        ]
    )
    return response.choices[0].message.content
