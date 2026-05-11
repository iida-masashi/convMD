import json

from convmd.exporters import export_files
from convmd.exporters.json_exporter import _parse_frontmatter


def test_parse_frontmatter():
    text = '---\ntitle: "Hello"\ntags: [a, b]\n---\n\nbody\n'
    fm, body = _parse_frontmatter(text)
    assert fm["title"] == "Hello"
    assert fm["tags"] == ["a", "b"]
    assert body.strip() == "body"


def test_json_export(tmp_path):
    md_a = tmp_path / "a.md"
    md_a.write_text('---\ntitle: "Alpha"\ntags: [x]\n---\n\nbody A\n', encoding="utf-8")
    md_b = tmp_path / "b.md"
    md_b.write_text("plain body B\n", encoding="utf-8")

    out = export_files("json", [md_a, md_b], tmp_path)
    assert out is not None and out.name == "export.json"
    data = json.loads(out.read_text(encoding="utf-8"))
    titles = {r["title"] for r in data}
    assert "Alpha" in titles
    assert "b" in titles  # fallback to stem


def test_unknown_format_returns_none(tmp_path):
    assert export_files("xyz", [], tmp_path) is None
    assert export_files("md", [], tmp_path) is None
