"""Pandoc-based exporter for epub / pdf output."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class PandocExporter:
    name = "pandoc"
    extension = ""

    def __init__(self, target: str) -> None:
        self.target = target
        self.extension = target

    def export(self, md_paths: list[Path], output_dir: Path) -> Path | None:
        if not shutil.which("pandoc"):
            logger.warning("pandoc not found on PATH; skipping %s export.", self.target)
            return None
        if not md_paths:
            return None

        out_path = output_dir / f"export.{self.extension}"
        cmd = ["pandoc", "-o", str(out_path), *[str(p) for p in md_paths]]
        if self.target == "pdf":
            cmd.extend(["--pdf-engine=xelatex"])
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"Pandoc wrote {self.target} to {out_path}")
            return out_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Pandoc {self.target} export failed: {e.stderr.strip()}")
            return None
