import os
from unittest.mock import MagicMock, patch

from convmd.core import gemini


def test_strip_code_fence():
    assert gemini.strip_code_fence("```markdown\nfoo\n```") == "foo"
    assert gemini.strip_code_fence("```\nfoo\n```") == "foo"
    assert gemini.strip_code_fence("plain") == "plain"


def test_is_configured():
    with patch.dict(os.environ, {}, clear=True):
        assert gemini.is_configured() is False
    with patch.dict(os.environ, {"GEMINI_API_KEY": "x"}, clear=True):
        assert gemini.is_configured() is True
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "x"}, clear=True):
        assert gemini.is_configured() is True


@patch("convmd.core.gemini.genai.Client")
def test_generate_text_strips_fences(mock_client_class):
    inst = MagicMock()
    mock_client_class.return_value = inst
    response = MagicMock()
    response.text = "```markdown\nhello\n```"
    inst.models.generate_content.return_value = response

    gemini.reset_usage()
    with patch.dict(os.environ, {"GEMINI_API_KEY": "x"}, clear=True):
        out = gemini.generate_text("prompt")
    assert out == "hello"


def test_generate_text_no_key():
    with patch.dict(os.environ, {}, clear=True):
        assert gemini.generate_text("prompt") is None


def test_usage_tracker_aggregates():
    tracker = gemini.UsageTracker()
    response = MagicMock()
    response.usage_metadata.prompt_token_count = 10
    response.usage_metadata.candidates_token_count = 5
    tracker.record("model-x", response)
    tracker.record("model-x", response)
    assert tracker.by_model["model-x"].input_tokens == 20
    assert tracker.by_model["model-x"].output_tokens == 10
    assert tracker.by_model["model-x"].calls == 2
