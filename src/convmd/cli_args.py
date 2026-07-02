"""CLI argument parsing and the typed RunConfig dataclass.

We deliberately do NOT use argparse subparsers — the legacy CLI shape ``convmd <target>``
is preserved verbatim. The ``find`` subcommand is detected by inspecting the first
positional argument before parsing (see ``cli.main``).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RunConfig:
    target: str
    output_dir: Path
    transform: str | None = None
    obsidian_vault: Path | None = None
    open_obsidian: bool = False
    notebooklm: str | None = None
    auto_link: bool = False
    depth: int = 0
    summary: bool = False
    slack_webhook: str | None = None
    interval: int = 0
    format: str = "md"
    bilingual: bool = False
    ocr: bool = False
    ai_extract: bool = False
    schema: str | None = None
    diff_only: bool = False
    no_cache: bool = False
    show_cost: bool = True
    podcast_limit: int = 1
    normalize_tags: bool = False
    tag_similarity_cutoff: float = 0.85
    render_js: bool = False
    extra: dict = field(default_factory=dict)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="convmd", description="Web to Markdown Toolkit")
    parser.add_argument("target", help="URL, local file path, or directory path to convert")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to write converted files to (default: ./output, or $CONVMD_OUTPUT_DIR).",
    )
    parser.add_argument("--transform", type=str, default=None)
    parser.add_argument(
        "--obsidian-vault",
        type=Path,
        default=None,
        help="Write output directly into this Obsidian vault. Takes precedence over "
        "--output-dir unless --output-dir was itself explicit on the command line "
        "and --obsidian-vault came only from a config file.",
    )
    parser.add_argument("--open-obsidian", action="store_true")
    parser.add_argument("--notebooklm", type=str, default=None)
    parser.add_argument("--auto-link", action="store_true")
    parser.add_argument("--depth", type=int, default=0)
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--slack-webhook", type=str, default=None)
    parser.add_argument("--interval", type=int, default=0)
    parser.add_argument("--format", choices=["md", "json", "epub", "pdf", "docx", "html"], default="md")
    parser.add_argument("--bilingual", action="store_true")
    parser.add_argument("--ocr", action="store_true", help="Enable AI OCR for images (e.g. IIIF manifests)")
    parser.add_argument("--ai-extract", action="store_true", help="Force autonomous extraction via LLM")
    parser.add_argument("--schema", type=str, default=None, help="Custom JSON schema for LLM extraction")
    parser.add_argument("--diff-only", action="store_true")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--no-cost", dest="show_cost", action="store_false")
    parser.add_argument("--podcast-limit", type=int, default=1)
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to an explicit YAML config file (overrides ~/.convmd.yaml and ./.convmd.yaml).",
    )
    parser.add_argument(
        "--normalize-tags",
        action="store_true",
        help="Normalize generated tags against existing tags in --obsidian-vault.",
    )
    parser.add_argument(
        "--tag-similarity-cutoff",
        type=float,
        default=0.85,
        help="Fuzzy match cutoff for tag normalization (0.0-1.0, default 0.85).",
    )
    parser.add_argument(
        "--render-js",
        action="store_true",
        help="Use Playwright to render JavaScript before extracting HTML.",
    )
    return parser


def build_find_parser() -> argparse.ArgumentParser:
    """Parser for the ``find`` subcommand. Used only when first arg is literally 'find'."""
    parser = argparse.ArgumentParser(prog="convmd find", description="Search converted Markdown")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--in", dest="search_dir", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("-i", "--ignore-case", action="store_true")
    parser.add_argument("--frontmatter-only", action="store_true")
    parser.add_argument("-s", "--semantic", action="store_true", help="Perform semantic search using ChromaDB and embeddings")
    parser.add_argument("--domain", type=str, default=None, help="Filter semantic search by source domain/string")
    parser.add_argument("--title", type=str, default=None, help="Filter semantic search by title string")
    return parser


def build_doctor_parser() -> argparse.ArgumentParser:
    """Parser for the ``doctor`` subcommand. Used only when first arg is literally 'doctor'."""
    return argparse.ArgumentParser(
        prog="convmd doctor", description="Run environment health checks"
    )


def _typed(
    args: argparse.Namespace,
    name: str,
    default: Any,
    expected_type: type | tuple[type, ...] | None,
) -> Any:
    """Tolerant attribute getter: returns the default if the attribute is missing
    or not of the expected type (e.g. a stray MagicMock from a partially-stubbed args object)."""
    value = getattr(args, name, default)
    if value is None:
        return default
    if expected_type and not isinstance(value, expected_type):
        return default
    return value


def to_run_config(args: argparse.Namespace, output_dir: Path) -> RunConfig:
    return RunConfig(
        target=str(args.target),
        output_dir=output_dir,
        transform=_typed(args, "transform", None, str),
        obsidian_vault=_typed(args, "obsidian_vault", None, Path),
        open_obsidian=_typed(args, "open_obsidian", False, bool),
        notebooklm=_typed(args, "notebooklm", None, str),
        auto_link=_typed(args, "auto_link", False, bool),
        depth=_typed(args, "depth", 0, int),
        summary=_typed(args, "summary", False, bool),
        slack_webhook=_typed(args, "slack_webhook", None, str),
        interval=_typed(args, "interval", 0, int),
        format=_typed(args, "format", "md", str),
        bilingual=_typed(args, "bilingual", False, bool),
        ocr=_typed(args, "ocr", False, bool),
        ai_extract=_typed(args, "ai_extract", False, bool),
        schema=_typed(args, "schema", None, str),
        diff_only=_typed(args, "diff_only", False, bool),
        no_cache=_typed(args, "no_cache", False, bool),
        show_cost=_typed(args, "show_cost", True, bool),
        podcast_limit=_typed(args, "podcast_limit", 1, int),
        normalize_tags=_typed(args, "normalize_tags", False, bool),
        tag_similarity_cutoff=_typed(args, "tag_similarity_cutoff", 0.85, float),
        render_js=_typed(args, "render_js", False, bool),
    )
