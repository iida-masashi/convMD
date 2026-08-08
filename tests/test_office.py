"""Tests for the office/PDF parser (anydoc primary, MarkItDown fallback, AI extract pass-through)."""

from unittest.mock import MagicMock, patch

import anydoc
import pytest

from convmd.parsers.office import convert_office_file


@patch("convmd.parsers.office.anydoc.to_markdown")
def test_convert_office_file_basic(mock_to_markdown, tmp_path):
    mock_to_markdown.return_value = "# Hello\n\nfrom pptx"

    src = tmp_path / "deck.pptx"
    src.write_bytes(b"\x00")  # presence only; anydoc is mocked

    out = convert_office_file(src, tmp_path)
    assert out is not None
    text = out.read_text(encoding="utf-8")
    assert "# Hello" in text
    assert 'tags:\n  - "local_file"\n  - "office"' in text


def test_convert_office_file_missing_returns_none(tmp_path):
    assert convert_office_file(tmp_path / "nope.pptx", tmp_path) is None


@patch("convmd.parsers.office.MarkItDown")
@patch("convmd.parsers.office.anydoc.to_markdown")
def test_convert_office_file_falls_back_to_markitdown(
    mock_to_markdown, mock_markitdown_class, tmp_path
):
    mock_to_markdown.side_effect = anydoc.UnsupportedError("scanned PDF, no text layer")
    mock_engine = MagicMock()
    mock_engine.convert.return_value = MagicMock(text_content="# Hello\n\nfrom markitdown")
    mock_markitdown_class.return_value = mock_engine

    src = tmp_path / "scanned.pdf"
    src.write_bytes(b"\x00")

    out = convert_office_file(src, tmp_path)
    assert out is not None
    text = out.read_text(encoding="utf-8")
    assert "from markitdown" in text


@patch("convmd.parsers.office.anydoc.to_markdown")
@patch("convmd.core.llm_extractor.extract_with_llm")
def test_convert_office_file_ai_extract_branch(mock_llm, mock_to_markdown, tmp_path):
    mock_to_markdown.return_value = "raw text body"

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


# Mojibake anydoc produced for a PDF with a broken embedded-font ToUnicode map
# (Type1 subset font, no usable glyph-to-Unicode mapping). Reproduced from a real
# extraction as a regression fixture rather than synthesized from scratch, since the
# failure mode is specific; one curly quote was normalized to straight for source
# encoding simplicity (General Punctuation isn't part of what _is_garbled counts).
_ANYDOC_MOJIBAKE = (
    "|U»T7||/>?0:;<KD=>0|\n|---|---|---|\n|v˝:˛fl)Uˇ˘—ZY||m0Q/DE'DQ|\n"
    "|¨£˚cU¸ ;<KK||uvwxyz:{|}~S9|\n|`´ˆ˜7¯ˆU»qD˘˙||hinom:345.pSqrst|\n"
    "|7SqTE¶:@A||A:de*0fg:hijk'ldm:|\n|>…‰@AY:¿@A||:ZY[\\]^_:<'ab>c@|\n"
) * 20

# MarkItDown's failure signature for the same class of PDF: literal (cid:N) tokens
# where it could not resolve a glyph to a Unicode codepoint.
_MARKITDOWN_MOJIBAKE = "\n".join(f"(cid:{i})" for i in range(500))


@patch("convmd.parsers.office.MarkItDown")
@patch("convmd.parsers.office.anydoc.to_markdown")
def test_convert_office_file_detects_garbled_anydoc_and_markitdown(
    mock_to_markdown, mock_markitdown_class, tmp_path
):
    """Both engines silently returning mojibake (no exception) must fail loudly, not write it."""
    mock_to_markdown.return_value = _ANYDOC_MOJIBAKE
    mock_engine = MagicMock()
    mock_engine.convert.return_value = MagicMock(text_content=_MARKITDOWN_MOJIBAKE)
    mock_markitdown_class.return_value = mock_engine

    src = tmp_path / "broken_font.pdf"
    src.write_bytes(b"\x00")

    assert convert_office_file(src, tmp_path) is None
    assert list(tmp_path.glob("*.md")) == []


@patch("convmd.parsers.office.MarkItDown")
@patch("convmd.parsers.office.anydoc.to_markdown")
def test_convert_office_file_recovers_when_markitdown_is_clean(
    mock_to_markdown, mock_markitdown_class, tmp_path
):
    """If anydoc is garbled but MarkItDown isn't, the MarkItDown text should still be used."""
    mock_to_markdown.return_value = _ANYDOC_MOJIBAKE
    mock_engine = MagicMock()
    mock_engine.convert.return_value = MagicMock(text_content="# Clean heading\n\nNormal prose.")
    mock_markitdown_class.return_value = mock_engine

    src = tmp_path / "recoverable.pdf"
    src.write_bytes(b"\x00")

    out = convert_office_file(src, tmp_path)
    assert out is not None
    assert "Clean heading" in out.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "text",
    [
        "The quick brown fox jumps over the lazy dog. " * 50,
        "これは正常な日本語のテキストです。" * 50,
        "\n".join(f"| {i} | {i * 2} | {i * 3} |" for i in range(50)),
        "x^2 + y^2 = z^2, where α β γ δ are physical constants. " * 20,
        # Accented Latin prose: a naive Latin-1-Supplement range check misflags these
        # (5-15% accented-character density) unless it excludes U+00C0-00FF.
        "Il était une fois un système très élégant qui créait des données. " * 30,
        "Die Übersetzung größerer Bücher benötigt häufig mehrere Wochen. " * 30,
        "A informação não está disponível na versão três da aplicação. " * 30,
        # Spanish inverted punctuation (¿¡) and degree/currency signs sit in the same
        # punctuation block (U+00A0-00BF) the check scans, so they need explicit exceptions.
        "¿Cómo estás? ¡Qué bien! Está aquí. " * 30,
        "Temperature ranges from -10°C to 40°C, tolerance ±0.5°, price £100. " * 20,
        # French/German guillemets («»/»«) and the German section sign (§) are dense in
        # dialogue-heavy prose and legal citations respectively; both are U+00A0-00BF
        # and were the tightest false-positive margin found (originally ~2.5-7% before
        # being added to the exception set).
        "« Bonjour », dit-il. « Comment allez-vous aujourd'hui ? » Elle répondit : « Très bien. » " * 20,
        "»Guten Tag«, sagte er. »Wie geht es Ihnen heute?« Sie antwortete: »Sehr gut, danke.« " * 20,
        "Nach § 823 Abs. 1 BGB und § 1004 BGB gilt: siehe § 12, § 34 und § 91a ZPO. " * 20,
    ],
    ids=[
        "english_prose",
        "japanese_prose",
        "table_heavy",
        "formula_heavy",
        "french_prose",
        "german_prose",
        "portuguese_prose",
        "spanish_punctuation",
        "degree_currency_signs",
        "french_guillemets",
        "german_guillemets",
        "german_legal_section_signs",
    ],
)
@patch("convmd.parsers.office.anydoc.to_markdown")
def test_convert_office_file_does_not_flag_clean_text(mock_to_markdown, tmp_path, text):
    """Guards against false positives on the kinds of content this check must not block."""
    mock_to_markdown.return_value = text

    src = tmp_path / "clean.pdf"
    src.write_bytes(b"\x00")

    out = convert_office_file(src, tmp_path)
    assert out is not None


@patch("convmd.parsers.office.MarkItDown")
@patch("convmd.parsers.office.anydoc.to_markdown")
def test_convert_office_file_empty_text_reports_no_text_layer(
    mock_to_markdown, mock_markitdown_class, tmp_path
):
    """A scanned image PDF (no text layer) must be diagnosed distinctly from font corruption."""
    mock_to_markdown.return_value = ""
    mock_engine = MagicMock()
    mock_engine.convert.return_value = MagicMock(text_content="   ")
    mock_markitdown_class.return_value = mock_engine

    src = tmp_path / "scanned_image.pdf"
    src.write_bytes(b"\x00")

    assert convert_office_file(src, tmp_path) is None
