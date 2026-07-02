"""YAML config file loader for convmd.

Resolution order (later overrides earlier):
  1. ``~/.convmd.yaml`` (personal defaults)
  2. ``./.convmd.yaml`` in the current working directory (project overrides)
  3. ``--config <path>`` if passed on the CLI (explicit overrides)
  4. CLI flags (highest priority — applied automatically by argparse)

Keys mirror argparse ``dest`` / ``RunConfig`` field names (snake_case).
Unknown keys are ignored with a warning so future fields don't break old configs.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


# Keys that must be coerced from string (YAML) into the type argparse expects.
# Without this, _typed() in cli_args.py drops them as "wrong type".
_COERCERS: dict[str, Any] = {
    "output_dir": Path,
    "obsidian_vault": Path,
    "depth": int,
    "interval": int,
    "podcast_limit": int,
}

# Allowed keys (argparse dests). Anything else is silently ignored.
_ALLOWED_KEYS = {
    "target",
    "output_dir",
    "transform",
    "obsidian_vault",
    "open_obsidian",
    "notebooklm",
    "auto_link",
    "depth",
    "summary",
    "slack_webhook",
    "interval",
    "format",
    "bilingual",
    "ocr",
    "ai_extract",
    "schema",
    "diff_only",
    "no_cache",
    "show_cost",
    "podcast_limit",
    "normalize_tags",
    "tag_similarity_cutoff",
    "render_js",
}


def _load_one(path: Path) -> dict[str, Any]:
    """Read one YAML file. Returns ``{}`` if missing, malformed, or non-dict."""
    if not path.is_file():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse config file {path}: {e}")
        return {}
    if data is None:
        return {}
    if not isinstance(data, dict):
        logger.warning(f"Config file {path} did not contain a YAML mapping; ignoring.")
        return {}
    return data


def _coerce(merged: dict[str, Any]) -> dict[str, Any]:
    """Apply per-key type coercion (Path / int) so argparse defaults match expected types."""
    out: dict[str, Any] = {}
    for key, value in merged.items():
        if key not in _ALLOWED_KEYS:
            logger.warning(f"Unknown config key '{key}' — ignoring.")
            continue
        coercer = _COERCERS.get(key)
        if coercer is not None and value is not None and not isinstance(value, coercer):
            try:
                out[key] = coercer(value)
            except (TypeError, ValueError) as e:
                logger.warning(f"Could not coerce config key '{key}'={value!r}: {e}; ignoring.")
                continue
        else:
            out[key] = value
    return out


def load_config(
    explicit_path: Path | None = None,
    *,
    home: Path | None = None,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Load and merge YAML config files in precedence order (later overrides earlier).

    Parameters are injectable so tests can avoid relying on the real filesystem.
    """
    home_path = (home or Path.home()) / ".convmd.yaml"
    cwd_path = (cwd or Path.cwd()) / ".convmd.yaml"

    merged: dict[str, Any] = {}
    for path in (home_path, cwd_path):
        merged.update(_load_one(path))
    if explicit_path is not None:
        merged.update(_load_one(explicit_path))

    return _coerce(merged)
