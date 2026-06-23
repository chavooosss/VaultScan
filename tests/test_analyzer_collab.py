from unittest.mock import patch

import pytest

import analyzer
from providers import anthropic_provider, openai_provider, gemini_provider

API_KEYS = {"claude": "sk-claude", "chatgpt": "sk-gpt", "gemini": "sk-gemini"}


@pytest.mark.asyncio
async def test_single_provider_skips_synthesis_entirely():
    with patch.object(anthropic_provider, "analyze_code", return_value="<div>claude</div>") as mock_claude, \
         patch.object(anthropic_provider, "synthesize") as mock_synth:
        result = await analyzer.analyze_code_collab("x = 1", "Python", ["claude"], API_KEYS)

    assert result == "<div>claude</div>"
    mock_claude.assert_called_once_with("x = 1", "Python", "sk-claude")
    mock_synth.assert_not_called()


@pytest.mark.asyncio
async def test_two_providers_run_in_parallel_and_get_synthesized():
    with patch.object(anthropic_provider, "analyze_code", return_value="<div>claude-finding</div>") as mock_claude, \
         patch.object(openai_provider, "analyze_code", return_value="<div>gpt-finding</div>") as mock_gpt, \
         patch.object(anthropic_provider, "synthesize", return_value="<div>merged</div>") as mock_synth:
        result = await analyzer.analyze_code_collab("x = 1", "Python", ["claude", "chatgpt"], API_KEYS)

    assert result == "<div>merged</div>"
    mock_claude.assert_called_once_with("x = 1", "Python", "sk-claude")
    mock_gpt.assert_called_once_with("x = 1", "Python", "sk-gpt")
    # first successful provider in the list becomes the synthesizer
    mock_synth.assert_called_once()
    synth_input = mock_synth.call_args.args[0]
    assert "claude-finding" in synth_input
    assert "gpt-finding" in synth_input
    assert mock_synth.call_args.args[1] == "sk-claude"


@pytest.mark.asyncio
async def test_partial_failure_still_synthesizes_from_survivors():
    with patch.object(anthropic_provider, "analyze_code", side_effect=RuntimeError("rate limited")), \
         patch.object(openai_provider, "analyze_code", return_value="<div>gpt-finding</div>"), \
         patch.object(gemini_provider, "analyze_code", return_value="<div>gemini-finding</div>"), \
         patch.object(openai_provider, "synthesize", return_value="<div>merged-from-2</div>") as mock_synth:
        result = await analyzer.analyze_code_collab("x = 1", "Python", ["claude", "chatgpt", "gemini"], API_KEYS)

    assert result == "<div>merged-from-2</div>"
    # synthesizer is the first SUCCESSFUL provider (claude failed, chatgpt is first survivor)
    mock_synth.assert_called_once()
    synth_input = mock_synth.call_args.args[0]
    assert "gpt-finding" in synth_input
    assert "gemini-finding" in synth_input
    assert "Claude" in synth_input  # failed-provider note mentions it
    assert mock_synth.call_args.args[1] == "sk-gpt"


@pytest.mark.asyncio
async def test_when_only_one_survives_no_synthesis_needed():
    with patch.object(anthropic_provider, "analyze_code", side_effect=RuntimeError("down")), \
         patch.object(openai_provider, "analyze_code", return_value="<div>gpt-only</div>") as mock_gpt, \
         patch.object(openai_provider, "synthesize") as mock_synth:
        result = await analyzer.analyze_code_collab("x = 1", "Python", ["claude", "chatgpt"], API_KEYS)

    assert result == "<div>gpt-only</div>"
    mock_synth.assert_not_called()


@pytest.mark.asyncio
async def test_all_providers_failing_raises():
    with patch.object(anthropic_provider, "analyze_code", side_effect=RuntimeError("down")), \
         patch.object(openai_provider, "analyze_code", side_effect=RuntimeError("down")):
        with pytest.raises(RuntimeError):
            await analyzer.analyze_code_collab("x = 1", "Python", ["claude", "chatgpt"], API_KEYS)


@pytest.mark.asyncio
async def test_analyze_multi_collab_single_provider():
    files = [{"path": "a.py", "code": "print(1)"}]
    with patch.object(anthropic_provider, "analyze_multi", return_value="<div>multi-claude</div>") as mock_multi:
        result = await analyzer.analyze_multi_collab(files, ["claude"], API_KEYS)

    assert result == "<div>multi-claude</div>"
    mock_multi.assert_called_once_with(files, "sk-claude")


@pytest.mark.asyncio
async def test_analyze_multi_collab_two_providers_synthesizes():
    files = [{"path": "a.py", "code": "print(1)"}]
    with patch.object(anthropic_provider, "analyze_multi", return_value="<div>claude-multi</div>"), \
         patch.object(gemini_provider, "analyze_multi", return_value="<div>gemini-multi</div>"), \
         patch.object(anthropic_provider, "synthesize", return_value="<div>merged-multi</div>") as mock_synth:
        result = await analyzer.analyze_multi_collab(files, ["claude", "gemini"], API_KEYS)

    assert result == "<div>merged-multi</div>"
    mock_synth.assert_called_once()
