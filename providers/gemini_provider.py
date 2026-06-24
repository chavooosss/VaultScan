from google import genai
from google.genai import types
from config import GEMINI_MODEL, MAX_TOKENS, PROVIDER_TIMEOUT_SECONDS
from prompts import get_system_prompt, get_synthesis_prompt, code_content, multi_intro, with_project_context
from providers.errors import ProviderNotConfigured

def _client(api_key: str):
    if not api_key:
        raise ProviderNotConfigured("Gemini (Google) için API key girilmemiş.")
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=PROVIDER_TIMEOUT_SECONDS * 1000),
    )

def _config(system_instruction: str):
    return types.GenerateContentConfig(
        system_instruction=system_instruction,
        max_output_tokens=MAX_TOKENS,
    )

def analyze_code(code: str, language: str, api_key: str, project_context: str = "", lang: str = "tr") -> str:
    content = with_project_context(code_content(code, language, lang), project_context)
    with _client(api_key) as client:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=content,
            config=_config(get_system_prompt(lang)),
        )
        return response.text

def analyze_multi(files: list, api_key: str, project_context: str = "", lang: str = "tr") -> str:
    parts = [f"### {f['path']}\n```\n{f['code']}\n```" for f in files]
    content = with_project_context(
        multi_intro(lang) + "\n\n".join(parts),
        project_context,
    )
    with _client(api_key) as client:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=content,
            config=_config(get_system_prompt(lang)),
        )
        return response.text

def synthesize(content: str, api_key: str, lang: str = "tr") -> str:
    with _client(api_key) as client:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=content,
            config=_config(get_synthesis_prompt(lang)),
        )
        return response.text
