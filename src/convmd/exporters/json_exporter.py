"""Aggregate converted Markdown files into a single structured JSON array."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n+", re.DOTALL)
_FIELD_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$', re.MULTILINE)


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm: dict[str, Any] = {}
    for key, raw in _FIELD_RE.findall(m.group(1)):
        val = raw.strip()
        if val.startswith('"') and val.endswith('"'):
            try:
                val = json.loads(val)
            except json.JSONDecodeError:
                val = val[1:-1]
        elif val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            val = [item.strip() for item in inner.split(",") if item.strip()] if inner else []
        fm[key] = val
    body = text[m.end() :]
    return fm, body


class JsonExporter:
    name = "json"
    extension = "json"

    def export(self, md_paths: list[Path], output_dir: Path) -> Path | None:
        records: list[dict[str, Any]] = []
        for path in md_paths:
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as e:
                logger.warning(f"Skipping {path}: {e}")
                continue
            fm, body = _parse_frontmatter(text)
            records.append(
                {
                    "file": str(path),
                    "title": fm.get("title", path.stem),
                    "source": fm.get("source"),
                    "date": fm.get("date"),
                    "tags": fm.get("tags", []),
                    "body": body,
                }
            )

        out_path = output_dir / "export.json"
        out_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info(f"Wrote JSON export with {len(records)} records to {out_path}")
        return out_path
