"""Tests for the office/PDF parser (markitdown wrapper + AI extract pass-through)."""

from unittest.mock import MagicMock, patch

from convmd.parsers.office import convert_office_file


@patch("convmd.parsers.office.MarkItDown")
def test_convert_office_file_basic(mock_markitdown_class, tmp_path):
    mock_engine = MagicMock()
    mock_engine.convert.return_value = MagicMock(text_content="# Hello\n\nfrom pptx")
    mock_markitdown_class.return_value = mock_engine

    src = tmp_path / "deck.pptx"
    src.write_bytes(b"\x00")  # presence only; MarkItDown is mocked

    out = convert_office_file(src, tmp_path)
    assert out is not None
    text = out.read_text(encoding="utf-8")
    assert "# Hello" in text
    assert 'tags:\n  - "local_file"\n  - "office"' in text


def test_convert_office_file_missing_returns_none(tmp_path):
    assert convert_office_file(tmp_path / "nope.pptx", tmp_path) is None


@patch("convmd.parsers.office.MarkItDown")
@patch("convmd.core.llm_extractor.extract_with_llm")
def test_convert_office_file_ai_extract_branch(mock_llm, mock_markitdown_class, tmp_path):
    mock_engine = MagicMock()
    mock_engine.convert.return_value = MagicMock(text_content="raw text body")
    mock_markitdown_class.return_value = mock_engine

    expected_out = tmp_path / "ai_out.md"
    expected_out.write_text("# AI extracted", encoding="utf-8")
    mock_llm.return_value = expected_out

    src = tmp_path / "doc.docx"
    src.write_bytes(b"\x00")

    out = convert_office_file(src, tmp_path, ai_extract=True, schema='{"foo":"bar"}')
    assert out == expected_out

    mock_llm.assert_called_once()
    _, kwargs = mock_llm.call_args
    assert kwargs["schema"] == '{"foo":"bar"}'
    assert kwargs["url"].endswith("doc.docx")
