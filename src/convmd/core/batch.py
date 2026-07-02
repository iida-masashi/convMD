"""Multi-target batch processing: --input-file target lists and --retry-failed tracking.

Failed targets are persisted as a plain newline-delimited text file in the output
directory (inspectable, no schema migration concerns), not the SQLite fetch cache in
core/cache.py -- that cache is about content diffing per-URL, not pass/fail tracking.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_FAILED_FILENAME = ".convmd_failed.txt"


def failed_list_path(output_dir: Path) -> Path:
    return output_dir / _FAILED_FILENAME


def read_targets_file(path: Path) -> list[str]:
    """Read one target (URL or file path) per line, ignoring blank lines and '#' comments."""
    if not path.is_file():
        logger.error(f"--input-file not found: {path}")
        return []
    targets: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            targets.append(stripped)
    return targets


def read_failed_targets(output_dir: Path) -> list[str]:
    """Return targets recorded as failed by a previous --input-file/--retry-failed run."""
    return read_targets_file(failed_list_path(output_dir))


def write_failed_targets(output_dir: Path, targets: list[str]) -> None:
    """Persist the current failure set, replacing any previous file.

    Called after every --input-file/--retry-failed run so the file always reflects
    only targets that failed on the most recent attempt (successes are dropped).
    """
    path = failed_list_path(output_dir)
    if not targets:
        if path.exists():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(targets) + "\n", encoding="utf-8")
