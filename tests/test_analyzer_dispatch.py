from unittest.mock import patch

import pytest

import analyzer
import providers
from providers import anthropic_provider, openai_provider, gemini_provider


def test_default_provider_is_claude():
    with patch.object(anthropic_provider, "analyze_code", return_value="claude-result") as mock_claude:
        result = analyzer.analyze_code("x = 1")
    assert result == "claude-result"
    mock_claude.assert_called_once_with("x = 1", "otomatik tespit")


def test_explicit_chatgpt_provider_dispatches_to_openai():
    with patch.object(openai_provider, "analyze_code", return_value="gpt-result") as mock_gpt:
        result = analyzer.analyze_code("x = 1", "Python", provider="chatgpt")
    assert result == "gpt-result"
    mock_gpt.assert_called_once_with("x = 1", "Python")


def test_explicit_gemini_provider_dispatches_to_gemini():
    with patch.object(gemini_provider, "analyze_code", return_value="gemini-result") as mock_gemini:
        result = analyzer.analyze_code("x = 1", provider="gemini")
    assert result == "gemini-result"
    mock_gemini.assert_called_once_with("x = 1", "otomatik tespit")


def test_analyze_multi_dispatches_by_provider():
    files = [{"path": "a.py", "code": "print(1)"}]
    with patch.object(openai_provider, "analyze_multi", return_value="multi-result") as mock_multi:
        result = analyzer.analyze_multi(files, provider="chatgpt")
    assert result == "multi-result"
    mock_multi.assert_called_once_with(files)


def test_unknown_provider_raises_value_error():
    with pytest.raises(ValueError):
        analyzer.analyze_code("x = 1", provider="not-a-real-provider")


def test_is_configured_reflects_provider_api_key():
    with patch.object(openai_provider, "OPENAI_API_KEY", ""):
        assert providers.is_configured("chatgpt") is False
    with patch.object(openai_provider, "OPENAI_API_KEY", "sk-fake"):
        assert providers.is_configured("chatgpt") is True
