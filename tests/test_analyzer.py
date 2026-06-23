from unittest.mock import MagicMock, patch

import analyzer


def _mock_message(text):
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    return msg


def test_analyze_code_returns_response_text():
    with patch.object(analyzer.client.messages, "create", return_value=_mock_message("<div>clean</div>")) as mock_create:
        result = analyzer.analyze_code("print(1)", "Python")

    assert result == "<div>clean</div>"
    kwargs = mock_create.call_args.kwargs
    assert kwargs["model"] == analyzer.MODEL
    assert "Dil: Python" in kwargs["messages"][0]["content"]
    assert "print(1)" in kwargs["messages"][0]["content"]


def test_analyze_code_uses_default_language_label():
    with patch.object(analyzer.client.messages, "create", return_value=_mock_message("ok")) as mock_create:
        analyzer.analyze_code("x = 1")

    assert "otomatik tespit" in mock_create.call_args.kwargs["messages"][0]["content"]


def test_analyze_multi_combines_files_in_prompt():
    files = [
        {"path": "a.py", "code": "print('a')"},
        {"path": "b.py", "code": "print('b')"},
    ]
    with patch.object(analyzer.client.messages, "create", return_value=_mock_message("<div>multi</div>")) as mock_create:
        result = analyzer.analyze_multi(files)

    assert result == "<div>multi</div>"
    content = mock_create.call_args.kwargs["messages"][0]["content"]
    assert "a.py" in content and "b.py" in content
    assert "print('a')" in content and "print('b')" in content
