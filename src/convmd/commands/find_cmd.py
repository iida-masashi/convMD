"""``convmd find <query>`` — full-text search across previously converted Markdown files.

Uses ``ripgrep`` (``rg --json``) when available; falls back to a pure-Python scan otherwise.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from convmd.config import get_output_dir

logger = logging.getLogger(__name__)


@dataclass
class Hit:
    path: Path
    line_no: int
    snippet: str


def _rg_search(query: str, root: Path, *, ignore_case: bool, limit: int) -> list[Hit]:
    cmd = ["rg", "--json", "--type", "md", query, str(root)]
    if ignore_case:
        cmd.insert(1, "-i")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return []
    hits: list[Hit] = []
    for raw in proc.stdout.splitlines():
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "match":
            continue
        data = obj.get("data", {})
        path = Path(data.get("path", {}).get("text", ""))
        line_no = int(data.get("line_number", 0))
        snippet = data.get("lines", {}).get("text", "").strip()
        hits.append(Hit(path=path, line_no=line_no, snippet=snippet))
        if len(hits) >= limit:
            break
    return hits


def _python_search(query: str, root: Path, *, ignore_case: bool, limit: int,
                    frontmatter_only: bool) -> list[Hit]:
    flags = re.IGNORECASE if ignore_case else 0
    pattern = re.compile(re.escape(query), flags)
    hits: list[Hit] = []
    for md in root.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        if frontmatter_only:
            if not text.startswith("---"):
                continue
            end = text.find("\n---", 3)
            if end == -1:
                continue
            text = text[: end + 4]

        for line_no, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                hits.append(Hit(path=md, line_no=line_no, snippet=line.strip()))
                if len(hits) >= limit:
                    return hits
    return hits


def run_find(args: argparse.Namespace) -> None:
    root = args.search_dir.resolve() if args.search_dir else get_output_dir()

    if getattr(args, "semantic", False):
        try:
            from convmd.core.vector_db import ChromaManager
            manager = ChromaManager(root)

            results = manager.search(args.query, limit=args.limit * 3) # Fetch more to allow for filtering

            if not results:
                print(f"No semantic matches found for '{args.query}' in {root}")
                return

            filtered_results = []
            for res in results:
                meta = res["metadata"]

                # Apply manual metadata filters
                if getattr(args, "domain", None) and args.domain not in meta.get("original_url", ""):
                    continue
                if getattr(args, "title", None) and args.title not in meta.get("title", ""):
                    continue

                filtered_results.append(res)
                if len(filtered_results) >= args.limit:
                    break

            if not filtered_results:
                print(f"No semantic matches passed the domain/title filters for '{args.query}' in {root}")
                return

            for res in filtered_results:
                meta = res["metadata"]
                dist = res["distance"]
                doc = res["document"]
                source = meta.get("source", "Unknown")
                title = meta.get("title", Path(source).name)
                # Print snippet safely
                snippet = doc[:150].replace("\n", " ") + "..." if len(doc) > 150 else doc.replace("\n", " ")
                print(f"[{title}] (Distance: {dist:.4f})\n  File: {source}\n  Snippet: {snippet}\n")
            return
        except ImportError:
            logger.error("chromadb is not installed. Run 'uv add chromadb' to enable semantic search.")
            return

    use_rg = shutil.which("rg") is not None and not args.frontmatter_only

    if use_rg:
        hits = _rg_search(args.query, root, ignore_case=args.ignore_case, limit=args.limit)
    else:
        hits = _python_search(
            args.query,
            root,
            ignore_case=args.ignore_case,
            limit=args.limit,
            frontmatter_only=args.frontmatter_only,
        )

    if not hits:
        print(f"No matches for '{args.query}' in {root}")
        return

    for hit in hits:
        rel = hit.path.relative_to(root) if hit.path.is_relative_to(root) else hit.path
        print(f"{rel}:{hit.line_no}: {hit.snippet}")
