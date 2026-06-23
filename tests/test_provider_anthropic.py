from unittest.mock import MagicMock, patch

import pytest

from providers import anthropic_provider
from providers.errors import ProviderNotConfigured


def _mock_client(text):
    client = MagicMock()
    client.messages.create.return_value = MagicMock(content=[MagicMock(text=text)])
    return client


def test_analyze_code_returns_response_text():
    client = _mock_client("<div>clean</div>")
    with patch.object(anthropic_provider, "_get_client", return_value=client):
        result = anthropic_provider.analyze_code("print(1)", "Python")

    assert result == "<div>clean</div>"
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["model"] == anthropic_provider.MODEL
    assert "Dil: Python" in kwargs["messages"][0]["content"]
    assert "print(1)" in kwargs["messages"][0]["content"]


def test_analyze_code_uses_default_language_label():
    client = _mock_client("ok")
    with patch.object(anthropic_provider, "_get_client", return_value=client):
        anthropic_provider.analyze_code("x = 1")

    assert "otomatik tespit" in client.messages.create.call_args.kwargs["messages"][0]["content"]


def test_analyze_multi_combines_files_in_prompt():
    files = [
        {"path": "a.py", "code": "print('a')"},
        {"path": "b.py", "code": "print('b')"},
    ]
    client = _mock_client("<div>multi</div>")
    with patch.object(anthropic_provider, "_get_client", return_value=client):
        result = anthropic_provider.analyze_multi(files)

    assert result == "<div>multi</div>"
    content = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "a.py" in content and "b.py" in content
    assert "print('a')" in content and "print('b')" in content


def test_synthesize_uses_synthesis_prompt_as_system():
    client = _mock_client("<div>synthesized</div>")
    with patch.object(anthropic_provider, "_get_client", return_value=client):
        result = anthropic_provider.synthesize("Claude analizi + ChatGPT analizi")

    assert result == "<div>synthesized</div>"
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["system"] == anthropic_provider.SYNTHESIS_PROMPT
    assert "Claude analizi" in kwargs["messages"][0]["content"]


def test_missing_api_key_raises_provider_not_configured():
    with patch.object(anthropic_provider, "ANTHROPIC_API_KEY", ""), \
         patch.object(anthropic_provider, "_client", None):
        with pytest.raises(ProviderNotConfigured):
            anthropic_provider.analyze_code("x = 1")
