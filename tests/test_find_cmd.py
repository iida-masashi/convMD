import argparse

from convmd.commands.find_cmd import _python_search, run_find


def _args(query, search_dir, **kwargs):
    return argparse.Namespace(
        query=query,
        search_dir=search_dir,
        limit=kwargs.get("limit", 50),
        ignore_case=kwargs.get("ignore_case", False),
        frontmatter_only=kwargs.get("frontmatter_only", False),
    )


def test_python_search_basic(tmp_path):
    (tmp_path / "a.md").write_text("hello world\ngoodbye\n", encoding="utf-8")
    (tmp_path / "b.md").write_text("nothing here\n", encoding="utf-8")
    hits = _python_search("hello", tmp_path, ignore_case=False, limit=10, frontmatter_only=False)
    assert len(hits) == 1
    assert hits[0].path.name == "a.md"
    assert hits[0].line_no == 1


def test_python_search_ignore_case(tmp_path):
    (tmp_path / "a.md").write_text("HELLO\n", encoding="utf-8")
    hits = _python_search("hello", tmp_path, ignore_case=True, limit=10, frontmatter_only=False)
    assert len(hits) == 1


def test_python_search_frontmatter_only(tmp_path):
    (tmp_path / "a.md").write_text(
        '---\ntitle: "hello in fm"\n---\n\nbody hello\n', encoding="utf-8"
    )
    hits = _python_search(
        "hello", tmp_path, ignore_case=False, limit=10, frontmatter_only=True
    )
    # Should match the frontmatter line but not the body
    assert all("body" not in h.snippet for h in hits)
    assert any("title" in h.snippet for h in hits)


def test_run_find_no_match(tmp_path, capsys):
    (tmp_path / "a.md").write_text("hello\n", encoding="utf-8")
    run_find(_args("xyz", tmp_path))
    out = capsys.readouterr().out
    assert "No matches" in out
