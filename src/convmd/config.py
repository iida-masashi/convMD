"""Output directory configuration. Lazily evaluated to avoid import-time side effects."""

from __future__ import annotations

import os
from pathlib import Path


def get_output_dir(override: Path | None = None) -> Path:
    """Return the configured output directory, creating it if necessary.

    Resolution order: explicit ``override`` arg > ``CONVMD_OUTPUT_DIR`` env > ``./output``.
    """
    if override is not None:
        out = override.resolve()
    else:
        env_value = os.environ.get("CONVMD_OUTPUT_DIR")
        if env_value:
            out = Path(env_value).resolve()
        else:
            out = (Path.cwd() / "output").resolve()
    out.mkdir(parents=True, exist_ok=True)
    return out
