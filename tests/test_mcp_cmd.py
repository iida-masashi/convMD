import argparse
import sys
from unittest.mock import MagicMock, patch

from convmd.cli import main
from convmd.commands.mcp_cmd import (
    convert_target_tool,
    create_mcp_server,
    run_mcp,
    search_markdown_tool,
)


def test_convert_target_tool_returns_markdown_and_saved_path(tmp_path):
    out_file = tmp_path / "converted.md"
    out_file.write_text("# Converted Heading\n\nBody text.", encoding="utf-8")

    with patch("convmd.commands.mcp_cmd.extract_phase", return_value=[out_file]), patch(
        "convmd.commands.mcp_cmd.transform_phase", side_effect=lambda files, cfg: files
    ):
        res = convert_target_tool(
            "https://example.com/post",
            output_dir=str(tmp_path),
            ai_extract=True,
        )

    assert f"<!-- file: {out_file} -->" in res
    assert "# Converted Heading" in res
    assert "Body text." in res


def test_convert_target_tool_no_files_generated(tmp_path):
    with patch("convmd.commands.mcp_cmd.extract_phase", return_value=[]):
        res = convert_target_tool("https://example.com/empty", output_dir=str(tmp_path))

    assert "Error: Failed to convert target 'https://example.com/empty'." in res


def test_search_markdown_tool_nonexistent_dir(tmp_path):
    missing = tmp_path / "does_not_exist"
    res = search_markdown_tool("test query", search_dir=str(missing))
    assert "No matches: directory" in res


def test_search_markdown_tool_semantic_formats_results(tmp_path):
    mock_manager = MagicMock()
    mock_manager.search.return_value = [
        {
            "document": "Chunk 1 text",
            "metadata": {"source": "doc1.md", "title": "Doc 1"},
            "distance": 0.1234,
        }
    ]
    with patch("convmd.core.vector_db.ChromaManager", return_value=mock_manager):
        res = search_markdown_tool("query", search_dir=str(tmp_path), semantic=True, limit=2)

    assert "[Doc 1] (Distance: 0.1234)" in res
    assert "File: doc1.md" in res
    assert "Snippet: Chunk 1 text" in res


def test_create_mcp_server_registers_tools():
    mcp_server = create_mcp_server()
    assert mcp_server is not None


def test_cli_mcp_subcommand_dispatches_to_run_mcp(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["convmd", "mcp", "--transport", "stdio"])
    with patch("convmd.commands.mcp_cmd.run_mcp") as mock_run_mcp:
        main()
        mock_run_mcp.assert_called_once()
        args = mock_run_mcp.call_args[0][0]
        assert args.transport == "stdio"


def test_run_mcp_invokes_server_run():
    mock_server = MagicMock()
    with patch("convmd.commands.mcp_cmd.create_mcp_server", return_value=mock_server):
        args = argparse.Namespace(transport="stdio")
        run_mcp(args)
        mock_server.run.assert_called_once_with(transport="stdio")
