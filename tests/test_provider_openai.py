from unittest.mock import MagicMock, patch

import pytest

from providers import openai_provider
from providers.errors import ProviderNotConfigured


def _mock_client(text):
    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=text))]
    )
    return client


def test_analyze_code_returns_response_text():
    client = _mock_client("<div>clean</div>")
    with patch.object(openai_provider, "_get_client", return_value=client):
        result = openai_provider.analyze_code("print(1)", "Python")

    assert result == "<div>clean</div>"
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == openai_provider.OPENAI_MODEL
    assert kwargs["messages"][0]["role"] == "system"
    assert "Dil: Python" in kwargs["messages"][1]["content"]
    assert "print(1)" in kwargs["messages"][1]["content"]


def test_analyze_code_uses_default_language_label():
    client = _mock_client("ok")
    with patch.object(openai_provider, "_get_client", return_value=client):
        openai_provider.analyze_code("x = 1")

    assert "otomatik tespit" in client.chat.completions.create.call_args.kwargs["messages"][1]["content"]


def test_analyze_multi_combines_files_in_prompt():
    files = [
        {"path": "a.py", "code": "print('a')"},
        {"path": "b.py", "code": "print('b')"},
    ]
    client = _mock_client("<div>multi</div>")
    with patch.object(openai_provider, "_get_client", return_value=client):
        result = openai_provider.analyze_multi(files)

    assert result == "<div>multi</div>"
    content = client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    assert "a.py" in content and "b.py" in content
    assert "print('a')" in content and "print('b')" in content


def test_missing_api_key_raises_provider_not_configured():
    with patch.object(openai_provider, "OPENAI_API_KEY", ""), \
         patch.object(openai_provider, "_client", None):
        with pytest.raises(ProviderNotConfigured):
            openai_provider.analyze_code("x = 1")
