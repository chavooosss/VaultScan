from unittest.mock import MagicMock, patch

import pytest

from providers import gemini_provider
from providers.errors import ProviderNotConfigured


def _mock_client(text):
    client = MagicMock()
    client.models.generate_content.return_value = MagicMock(text=text)
    return client


def test_analyze_code_returns_response_text():
    client = _mock_client("<div>clean</div>")
    with patch.object(gemini_provider, "_get_client", return_value=client):
        result = gemini_provider.analyze_code("print(1)", "Python")

    assert result == "<div>clean</div>"
    kwargs = client.models.generate_content.call_args.kwargs
    assert kwargs["model"] == gemini_provider.GEMINI_MODEL
    assert "Dil: Python" in kwargs["contents"]
    assert "print(1)" in kwargs["contents"]
    assert kwargs["config"].system_instruction == gemini_provider.SYSTEM_PROMPT


def test_analyze_code_uses_default_language_label():
    client = _mock_client("ok")
    with patch.object(gemini_provider, "_get_client", return_value=client):
        gemini_provider.analyze_code("x = 1")

    assert "otomatik tespit" in client.models.generate_content.call_args.kwargs["contents"]


def test_analyze_multi_combines_files_in_prompt():
    files = [
        {"path": "a.py", "code": "print('a')"},
        {"path": "b.py", "code": "print('b')"},
    ]
    client = _mock_client("<div>multi</div>")
    with patch.object(gemini_provider, "_get_client", return_value=client):
        result = gemini_provider.analyze_multi(files)

    assert result == "<div>multi</div>"
    content = client.models.generate_content.call_args.kwargs["contents"]
    assert "a.py" in content and "b.py" in content
    assert "print('a')" in content and "print('b')" in content


def test_synthesize_uses_synthesis_prompt_as_system():
    client = _mock_client("<div>synthesized</div>")
    with patch.object(gemini_provider, "_get_client", return_value=client):
        result = gemini_provider.synthesize("Claude analizi + ChatGPT analizi")

    assert result == "<div>synthesized</div>"
    kwargs = client.models.generate_content.call_args.kwargs
    assert "Claude analizi" in kwargs["contents"]
    assert kwargs["config"].system_instruction == gemini_provider.SYNTHESIS_PROMPT


def test_missing_api_key_raises_provider_not_configured():
    with patch.object(gemini_provider, "GEMINI_API_KEY", ""), \
         patch.object(gemini_provider, "_client", None):
        with pytest.raises(ProviderNotConfigured):
            gemini_provider.analyze_code("x = 1")
