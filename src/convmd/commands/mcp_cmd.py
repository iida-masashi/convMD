"""``convmd mcp`` — Model Context Protocol (MCP) server for convMD.

Exposes convMD's URL/file conversion and Markdown search capabilities as MCP tools
so AI agents (Claude Desktop, Cursor, Antigravity, etc.) can invoke them directly.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import time
from pathlib import Path
from typing import Any

from convmd.cli_args import RunConfig
from convmd.commands.find_cmd import _python_search, _rg_search
from convmd.config import get_output_dir
from convmd.pipeline import extract_phase, transform_phase

logger = logging.getLogger(__name__)


def convert_target_tool(
    target: str,
    output_dir: str | None = None,
    ocr: bool = False,
    ai_extract: bool = False,
    render_js: bool = False,
    transform: str | None = None,
) -> str:
    """Convert a URL or local file into Markdown and return the generated content."""
    out_path = get_output_dir(Path(output_dir) if output_dir else None)
    cfg = RunConfig(
        target=target,
        output_dir=out_path,
        ocr=ocr,
        ai_extract=ai_extract,
        render_js=render_js,
        transform=transform,
        show_cost=False,
    )
    start_time = time.time()
    files = extract_phase(cfg, start_time)
    if not files:
        return f"Error: Failed to convert target '{target}'."

    files = transform_phase(files, cfg)
    sections: list[str] = []
    for md_file in files:
        try:
            body = md_file.read_text(encoding="utf-8", errors="replace")
            sections.append(f"<!-- file: {md_file} -->\n{body}")
        except OSError as e:
            sections.append(f"<!-- file: {md_file} (read error: {e}) -->")
    return "\n\n".join(sections)


def search_markdown_tool(
    query: str,
    search_dir: str | None = None,
    semantic: bool = False,
    limit: int = 10,
    ignore_case: bool = True,
) -> str:
    """Search previously converted Markdown files by keyword or semantic similarity."""
    root = Path(search_dir).resolve() if search_dir else get_output_dir()
    if not root.exists():
        return f"No matches: directory '{root}' does not exist."

    if semantic:
        try:
            from convmd.core.vector_db import ChromaManager

            manager = ChromaManager(root)
            results = manager.search(query, limit=limit)
            if not results:
                return f"No semantic matches found for '{query}' in {root}"
            lines: list[str] = []
            for res in results[:limit]:
                meta = res.get("metadata", {})
                dist = res.get("distance", 0.0)
                doc = str(res.get("document", "")).replace("\n", " ")
                source = meta.get("source", "Unknown")
                title = meta.get("title", Path(str(source)).name)
                snippet = doc[:200] + "..." if len(doc) > 200 else doc
                lines.append(f"[{title}] (Distance: {dist:.4f})\n  File: {source}\n  Snippet: {snippet}")
            return "\n\n".join(lines)
        except Exception as e:
            return f"Error running semantic search: {e}"

    use_rg = shutil.which("rg") is not None
    if use_rg:
        hits = _rg_search(query, root, ignore_case=ignore_case, limit=limit)
    else:
        hits = _python_search(
            query, root, ignore_case=ignore_case, limit=limit, frontmatter_only=False
        )

    if not hits:
        return f"No matches for '{query}' in {root}"

    out_lines: list[str] = []
    for hit in hits:
        rel = hit.path.relative_to(root) if hit.path.is_relative_to(root) else hit.path
        out_lines.append(f"{rel}:{hit.line_no}: {hit.snippet}")
    return "\n".join(out_lines)


def create_mcp_server() -> Any:
    """Build and return the MCP server instance with convMD tools registered."""
    try:
        from mcp.server.mcpserver import MCPServer as ServerCls  # type: ignore[import-not-found]
    except ImportError:
        from mcp.server.fastmcp import (  # type: ignore[import-not-found, attr-defined, no-redef]
            FastMCP as ServerCls,
        )

    mcp: Any = ServerCls("convMD")
    mcp.tool(name="convert_target")(convert_target_tool)
    mcp.tool(name="search_markdown")(search_markdown_tool)
    return mcp


def run_mcp(args: argparse.Namespace) -> None:
    """Entry point for ``convmd mcp``."""
    try:
        server = create_mcp_server()
    except ImportError:
        logger.error("mcp is not installed. Run 'uv sync --extra mcp' to enable the MCP server.")
        return

    transport = getattr(args, "transport", "stdio") or "stdio"
    server.run(transport=transport)
