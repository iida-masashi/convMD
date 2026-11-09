"""PDF/Office の URL 取込で、frontmatter の source: が一時パスでなく元URLになることの回帰テスト。

一時ディレクトリに落としたファイルのパスを source: に書くと、取込後に原典を辿れなくなる
（cpg Vault で 100件超の資料が一時パスの source: になっていた）。
"""
from unittest.mock import patch

import convmd.parsers.office as office


def _run(tmp_path, **kw):
    f = tmp_path / "report.pdf"
    f.write_bytes(b"%PDF-1.4 dummy")
    out = tmp_path / "out"
    out.mkdir()
    with patch.object(office, "_convert_to_markdown_text", return_value="# Title\n\nbody text"):
        res = office.convert_office_file(f, out, **kw)
    assert res is not None
    return res.read_text(encoding="utf-8")


def test_source_url_is_written_instead_of_temp_path(tmp_path):
    text = _run(tmp_path, source_url="https://example.com/docs/report.pdf")
    assert 'source: "https://example.com/docs/report.pdf"' in text
    assert str(tmp_path).replace("\\", "\\\\") not in text
    assert "web_clip" in text


def test_local_file_keeps_local_path_when_no_source_url(tmp_path):
    text = _run(tmp_path)
    assert "local_file" in text
    assert "report.pdf" in text
