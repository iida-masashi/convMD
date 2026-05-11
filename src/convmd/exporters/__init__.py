"""Pluggable exporters for converting batches of Markdown files into other formats."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)


class Exporter(Protocol):
    name: str
    extension: str

    def export(self, md_paths: list[Path], output_dir: Path) -> Path | None: ...


def get_exporter(name: str) -> Exporter | None:
    if name == "md":
        return None
    if name == "json":
        from convmd.exporters.json_exporter import JsonExporter

        return JsonExporter()
    if name in {"epub", "pdf"}:
        from convmd.exporters.pandoc_exporter import PandocExporter

        return PandocExporter(target=name)
    logger.warning(f"Unknown export format: {name}")
    return None


def export_files(name: str, md_paths: list[Path], output_dir: Path) -> Path | None:
    exporter = get_exporter(name)
    if exporter is None:
        return None
    return exporter.export(md_paths, output_dir)
