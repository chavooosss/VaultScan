from openai import OpenAI
from config import OPENAI_MODEL, MAX_TOKENS
from prompts import SYSTEM_PROMPT, SYNTHESIS_PROMPT
from providers.errors import ProviderNotConfigured

def _client(api_key: str):
    if not api_key:
        raise ProviderNotConfigured("ChatGPT (OpenAI) için API key girilmemiş.")
    return OpenAI(api_key=api_key)

def analyze_code(code: str, language: str, api_key: str) -> str:
    response = _client(api_key).chat.completions.create(
        model=OPENAI_MODEL,
        max_completion_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Dil: {language}\n\nKod:\n```\n{code}\n```"}
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

def analyze_multi(files: list, api_key: str) -> str:
    parts = [f"### {f['path']}\n```\n{f['code']}\n```" for f in files]
    content = "Aşağıdaki dosyalar birbiriyle ilişkili, birlikte analiz et:\n\n" + "\n\n".join(parts)
    response = _client(api_key).chat.completions.create(
        model=OPENAI_MODEL,
        max_completion_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content}
        ]
    )
    return response.choices[0].message.content
