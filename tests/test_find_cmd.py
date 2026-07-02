import argparse
import json
from unittest.mock import MagicMock, patch

from convmd.commands.find_cmd import _python_search, _rg_search, run_find


def _args(query, search_dir, **kwargs):
    return argparse.Namespace(
        query=query,
        search_dir=search_dir,
        limit=kwargs.get("limit", 50),
        ignore_case=kwargs.get("ignore_case", False),
        frontmatter_only=kwargs.get("frontmatter_only", False),
        semantic=kwargs.get("semantic", False),
        domain=kwargs.get("domain", None),
        title=kwargs.get("title", None),
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


def _rg_json_line(path, line_number, text):
    return json.dumps(
        {
            "type": "match",
            "data": {
                "path": {"text": path},
                "line_number": line_number,
                "lines": {"text": text},
            },
        }
    )


def test_rg_search_parses_json_output(tmp_path):
    stdout = "\n".join(
        [
            _rg_json_line("a.md", 3, "hello world\n"),
            json.dumps({"type": "begin", "data": {}}),
            "not json",
        ]
    )
    mock_proc = MagicMock(stdout=stdout)
    with patch("convmd.commands.find_cmd.subprocess.run", return_value=mock_proc):
        hits = _rg_search("hello", tmp_path, ignore_case=False, limit=10)
    assert len(hits) == 1
    assert hits[0].path.name == "a.md"
    assert hits[0].line_no == 3
    assert hits[0].snippet == "hello world"


def test_rg_search_respects_limit(tmp_path):
    stdout = "\n".join(_rg_json_line(f"{i}.md", 1, "hit") for i in range(5))
    mock_proc = MagicMock(stdout=stdout)
    with patch("convmd.commands.find_cmd.subprocess.run", return_value=mock_proc):
        hits = _rg_search("hit", tmp_path, ignore_case=False, limit=2)
    assert len(hits) == 2


def test_rg_search_missing_binary_returns_empty(tmp_path):
    with patch("convmd.commands.find_cmd.subprocess.run", side_effect=FileNotFoundError):
        assert _rg_search("hello", tmp_path, ignore_case=False, limit=10) == []


def test_run_find_semantic_no_results(tmp_path, capsys):
    mock_manager = MagicMock()
    mock_manager.search.return_value = []
    with patch("convmd.core.vector_db.ChromaManager", return_value=mock_manager):
        run_find(_args("hello", tmp_path, semantic=True))
    out = capsys.readouterr().out
    assert "No semantic matches found" in out


def test_run_find_semantic_prints_results(tmp_path, capsys):
    mock_manager = MagicMock()
    mock_manager.search.return_value = [
        {
            "document": "some matching document text",
            "metadata": {"source": "a.md", "title": "A", "original_url": "https://example.com"},
            "distance": 0.1234,
        }
    ]
    with patch("convmd.core.vector_db.ChromaManager", return_value=mock_manager):
        run_find(_args("hello", tmp_path, semantic=True))
    out = capsys.readouterr().out
    assert "A" in out
    assert "0.1234" in out
    assert "a.md" in out


def test_run_find_semantic_domain_filter_excludes_all(tmp_path, capsys):
    mock_manager = MagicMock()
    mock_manager.search.return_value = [
        {
            "document": "doc",
            "metadata": {"source": "a.md", "title": "A", "original_url": "https://other.com"},
            "distance": 0.1,
        }
    ]
    with patch("convmd.core.vector_db.ChromaManager", return_value=mock_manager):
        run_find(_args("hello", tmp_path, semantic=True, domain="example.com"))
    out = capsys.readouterr().out
    assert "No semantic matches passed the domain/title filters" in out


def test_run_find_semantic_import_error(tmp_path, capsys):
    with patch.dict("sys.modules", {"convmd.core.vector_db": None}):
        run_find(_args("hello", tmp_path, semantic=True))
    # ImportError path logs via logger, not print; just ensure no crash and no stdout match text
    out = capsys.readouterr().out
    assert "No semantic matches" not in out
