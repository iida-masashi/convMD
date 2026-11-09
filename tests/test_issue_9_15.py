"""Regression tests for convMD issues #9 (pypdf fallback), #10 (SEC UA hint),
#11 (quality gate), #12 (origin line), #13 (no stray dirs), #15 (evidence_type)."""

import logging
from pathlib import Path
from unittest.mock import patch

import convmd.core.http as http
import convmd.parsers.office as office
from convmd.core.quality import add_origin_line, check_output


def _pdf(tmp_path: Path) -> Path:
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.4 dummy")
    return f


# --- #9 -----------------------------------------------------------------
def test_pypdf_used_when_engines_fail(tmp_path):
    with (
        patch.object(office, "_convert_with_engines", return_value=None),
        patch.object(office, "_pypdf_markdown", return_value="<!-- p.1 -->\n\n有価証券報告書の本文です。" * 3),
    ):
        assert "有価証券報告書" in (office._convert_to_markdown_text(_pdf(tmp_path)) or "")


def test_pypdf_preferred_when_engine_lost_japanese(tmp_path):
    mojibake = "Ã¯ ABC def ghi " * 40
    jp = "<!-- p.1 -->\n\n" + "売上高は増加しました。" * 20
    with (
        patch.object(office, "_convert_with_engines", return_value=mojibake),
        patch.object(office, "_pypdf_markdown", return_value=jp),
    ):
        assert office._convert_to_markdown_text(_pdf(tmp_path)) == jp


def test_engine_text_kept_when_pypdf_not_better(tmp_path):
    good = "売上高は増加しました。" * 20
    with (
        patch.object(office, "_convert_with_engines", return_value=good),
        patch.object(office, "_pypdf_markdown", return_value="<!-- p.1 -->\n\n" + good),
    ):
        assert office._convert_to_markdown_text(_pdf(tmp_path)) == good


def test_non_pdf_skips_pypdf(tmp_path):
    f = tmp_path / "a.docx"
    f.write_bytes(b"x")
    with (
        patch.object(office, "_convert_with_engines", return_value="body"),
        patch.object(office, "_pypdf_markdown") as m,
    ):
        assert office._convert_to_markdown_text(f) == "body"
        m.assert_not_called()


# --- #10 ----------------------------------------------------------------
def test_ua_hint_logged_for_sec_403(caplog):
    with caplog.at_level(logging.ERROR, logger="convmd.core.http"):
        http._log_ua_hint("https://www.sec.gov/Archives/x.htm", 403)
    assert "User-Agent" in caplog.text and "--sec-user-agent" in caplog.text


def test_ua_hint_silent_for_other_hosts(caplog):
    with caplog.at_level(logging.ERROR, logger="convmd.core.http"):
        http._log_ua_hint("https://example.com/a", 403)
        http._log_ua_hint("https://www.sec.gov/a", 404)
    assert caplog.text == ""


def test_sec_ua_env_override(monkeypatch):
    monkeypatch.setenv("CONVMD_SEC_USER_AGENT", "Test Name test@example.com")
    h = http._with_sec_user_agent("https://www.sec.gov/a", None)
    assert h is not None and h["User-Agent"] == "Test Name test@example.com"


# --- #11 ----------------------------------------------------------------
def test_check_output_flags_empty_and_big(tmp_path):
    empty = tmp_path / "e.md"
    empty.write_text('---\ntitle: "t"\nsource: "https://e.com/a"\n---\n', encoding="utf-8")
    assert any("empty" in p for p in check_output(empty))
    big = tmp_path / "b.md"
    big.write_text("---\ntitle: t\n---\n" + "あ" * 400_000, encoding="utf-8")
    assert any("MB" in p for p in check_output(big))


def test_check_output_clean_file(tmp_path):
    f = tmp_path / "ok.md"
    f.write_text("---\ntitle: t\n---\n" + "通常の本文です。" * 10, encoding="utf-8")
    assert check_output(f) == []


# --- #12 ----------------------------------------------------------------
def test_add_origin_line_lf_and_idempotent(tmp_path):
    f = tmp_path / "a.md"
    f.write_bytes(b'---\ntitle: "t"\nsource: "https://example.com/x.pdf"\n---\n\n# H\n')
    assert add_origin_line(f) is True
    text = f.read_bytes().decode("utf-8")
    assert text.endswith("---\n\n> \u539f\u5178URL: https://example.com/x.pdf\n\n# H\n")
    assert add_origin_line(f) is False


def test_add_origin_line_keeps_crlf_and_skips_local_source(tmp_path):
    f = tmp_path / "c.md"
    f.write_bytes(b'---\r\nsource: "https://e.com/a"\r\n---\r\nbody\r\n')
    assert add_origin_line(f) is True
    assert b"\n" not in f.read_bytes().replace(b"\r\n", b"")
    g = tmp_path / "l.md"
    g.write_bytes(b'---\nsource: "C:\\\\tmp\\\\a.pdf"\n---\nbody\n')
    assert add_origin_line(g) is False


# --- #13 ----------------------------------------------------------------
def test_process_images_creates_no_dir_without_images(tmp_path):
    from convmd.core.download import process_images

    out = process_images("text only", "https://e.com", tmp_path)
    assert out == "text only"
    assert not (tmp_path / "images").exists()


def test_embed_phase_skipped_with_no_cache(tmp_path):
    from convmd.cli_args import RunConfig
    from convmd.pipeline import embed_phase

    f = tmp_path / "a.md"
    f.write_text("x", encoding="utf-8")
    cfg = RunConfig(target="x", output_dir=tmp_path, no_cache=True)
    embed_phase([f], cfg)
    assert not (tmp_path / ".chroma_db").exists()


# --- #15 ----------------------------------------------------------------
def test_ocr_output_has_evidence_type(tmp_path):
    f = _pdf(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    with (
        patch.object(office, "_convert_to_markdown_text", return_value=None),
        patch("convmd.core.gemini.is_configured", return_value=True),
        patch("convmd.core.gemini.transcribe_pdf", return_value="OCR text body here"),
    ):
        res = office.convert_office_file(f, out, ocr=True)
    assert res is not None and "evidence_type: " in res.read_text(encoding="utf-8")
