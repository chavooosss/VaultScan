from openai import OpenAI
from config import OPENAI_MODEL, MAX_TOKENS, PROVIDER_TIMEOUT_SECONDS
from prompts import get_system_prompt, get_synthesis_prompt, code_content, multi_intro, with_project_context
from providers.errors import ProviderNotConfigured

def _client(api_key: str):
    if not api_key:
        raise ProviderNotConfigured("ChatGPT (OpenAI) için API key girilmemiş.")
    return OpenAI(api_key=api_key, timeout=PROVIDER_TIMEOUT_SECONDS)

def _content_or_raise(content, lang: str) -> str:
    # OpenAI bazı durumlarda (içerik filtresi, ya da modelin sadece tool-call
    # üretmesi) content=None döndürebilir — bunu sessizce "başarılı" sonuç
    # gibi geçirmek yerine, collab katmanının zaten bildiği başarısız-provider
    # yoluna düşürmek için açıkça hata fırlatıyoruz.
    if content is None:
        if lang == "en":
            raise RuntimeError("ChatGPT (OpenAI) returned an empty response (possibly a content filter or tool-call).")
        raise RuntimeError("ChatGPT (OpenAI) boş bir yanıt döndürdü (içerik filtresi veya tool-call nedeniyle olabilir).")
    return content

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
    return _content_or_raise(response.choices[0].message.content, lang)

def synthesize(content: str, api_key: str, lang: str = "tr") -> str:
    response = _client(api_key).chat.completions.create(
        model=OPENAI_MODEL,
        max_completion_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": get_synthesis_prompt(lang)},
            {"role": "user", "content": content}
        ]
    )
    return _content_or_raise(response.choices[0].message.content, lang)

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
    return _content_or_raise(response.choices[0].message.content, lang)
