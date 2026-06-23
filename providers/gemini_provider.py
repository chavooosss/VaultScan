from google import genai
from google.genai import types
from config import GEMINI_MODEL, MAX_TOKENS
from prompts import SYSTEM_PROMPT, SYNTHESIS_PROMPT
from providers.errors import ProviderNotConfigured

def _client(api_key: str):
    if not api_key:
        raise ProviderNotConfigured("Gemini (Google) için API key girilmemiş.")
    return genai.Client(api_key=api_key)

def _config(system_instruction: str):
    return types.GenerateContentConfig(
        system_instruction=system_instruction,
        max_output_tokens=MAX_TOKENS,
    )

def analyze_code(code: str, language: str, api_key: str) -> str:
    response = _client(api_key).models.generate_content(
        model=GEMINI_MODEL,
        contents=f"Dil: {language}\n\nKod:\n```\n{code}\n```",
        config=_config(SYSTEM_PROMPT),
    )
    return response.text

def analyze_multi(files: list, api_key: str) -> str:
    parts = [f"### {f['path']}\n```\n{f['code']}\n```" for f in files]
    content = "Aşağıdaki dosyalar birbiriyle ilişkili, birlikte analiz et:\n\n" + "\n\n".join(parts)
    response = _client(api_key).models.generate_content(
        model=GEMINI_MODEL,
        contents=content,
        config=_config(SYSTEM_PROMPT),
    )
    return response.text

def synthesize(content: str, api_key: str) -> str:
    response = _client(api_key).models.generate_content(
        model=GEMINI_MODEL,
        contents=content,
        config=_config(SYNTHESIS_PROMPT),
    )
    return response.text
