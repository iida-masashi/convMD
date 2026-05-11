"""Medium article fetcher (Readability fallback)."""

from __future__ import annotations

import logging
from pathlib import Path

from markdownify import markdownify as md
from readability import Document  # type: ignore

from convmd.core.download import process_images
from convmd.core.http import get_html
from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)


def convert_medium(url: str, output_dir: Path) -> Path | None:
    html = get_html(url)
    if not html:
        return None

    doc = Document(html)
    title = doc.title()
    md_body = md(doc.summary(), heading_style="ATX")
    md_body = process_images(md_body, url, output_dir)
    frontmatter = generate_frontmatter(title, url, tags=["medium", "blog"])

    path = output_dir / f"{sanitize_filename(title)}.md"
    path.write_text(frontmatter + md_body, encoding="utf-8")
    logger.info(f"Saved Medium article to {path}")
    return path
