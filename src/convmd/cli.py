"""Top-level CLI entry point.

The heavy lifting now lives in ``pipeline.run_pipeline`` and ``routing.dispatch_url``.
This module remains the public ``convmd`` entry point and re-exports a handful of
symbols (``process_target``, ``transform_markdown_with_gemini``, ``upload_to_notebooklm``)
that legacy tests patch.
"""

from __future__ import annotations

import argparse  # noqa: F401 — re-exported for tests that patch convmd.cli.argparse.ArgumentParser
import logging
import sys
import time  # noqa: F401 — re-exported for tests that patch convmd.cli.time.time
from pathlib import Path

from convmd.cli_args import build_parser, to_run_config
from convmd.config import get_output_dir
from convmd.config_file import load_config
from convmd.core.transform import transform_markdown_with_gemini  # noqa: F401 — test patch surface
from convmd.integrations.notebooklm import upload_to_notebooklm  # noqa: F401 — test patch surface
from convmd.pipeline import process_target, run_pipeline  # noqa: F401 — test patch surface

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _resolve_output_dir(args: argparse.Namespace) -> Path:
    obsidian_vault = getattr(args, "obsidian_vault", None)
    if obsidian_vault:
        path = Path(obsidian_vault).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path
    output_dir = getattr(args, "output_dir", None)
    return get_output_dir(Path(output_dir) if output_dir else None)


def _sniff_config_flag(argv: list[str]) -> Path | None:
    """Pre-scan argv for ``--config <path>`` or ``--config=<path>`` without invoking argparse."""
    for i, token in enumerate(argv):
        if token == "--config" and i + 1 < len(argv):
            return Path(argv[i + 1])
        if token.startswith("--config="):
            return Path(token.split("=", 1)[1])
    return None


def _maybe_run_find_subcommand() -> bool:
    """If the user invoked ``convmd find <query>``, handle it and return True."""
    if len(sys.argv) > 1 and sys.argv[1] == "find":
        from convmd.cli_args import build_find_parser
        from convmd.commands.find_cmd import run_find

        find_parser = build_find_parser()
        find_args = find_parser.parse_args(sys.argv[2:])
        run_find(find_args)
        return True
    return False


def main() -> None:
    if _maybe_run_find_subcommand():
        return

    parser = build_parser()
    # Two-pass parse so YAML config can populate defaults before the real parse.
    # We sniff --config manually rather than calling parse_known_args(), because
    # the latter still validates the choice-typed flags (e.g. --format) and would
    # fail under tests that monkeypatch parse_args() but leave sys.argv alone.
    explicit_config = _sniff_config_flag(sys.argv[1:])
    yaml_defaults = load_config(explicit_config)
    if yaml_defaults:
        parser.set_defaults(**yaml_defaults)
    args = parser.parse_args()

    output_dir = _resolve_output_dir(args)
    logger.info(f"Output directory set to: {output_dir}")

    cfg = to_run_config(args, output_dir)
    run_pipeline(cfg)


if __name__ == "__main__":
    main()
