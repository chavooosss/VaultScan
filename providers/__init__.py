from . import anthropic_provider, openai_provider, gemini_provider
from providers.errors import ProviderNotConfigured

PROVIDERS = {
    "claude": anthropic_provider,
    "chatgpt": openai_provider,
    "gemini": gemini_provider,
}

PROVIDER_LABELS = {
    "claude": "Claude (Anthropic)",
    "chatgpt": "ChatGPT (OpenAI)",
    "gemini": "Gemini (Google)",
}

DEFAULT_PROVIDER = "claude"

def get_provider(name: str):
    module = PROVIDERS.get(name)
    if module is None:
        raise ValueError(f"Bilinmeyen AI sağlayıcı: {name}")
    return module

__all__ = ["PROVIDERS", "PROVIDER_LABELS", "DEFAULT_PROVIDER", "get_provider", "ProviderNotConfigured"]
