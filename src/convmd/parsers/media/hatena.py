"""Hatena Blog / Hatena Bookmark fetcher (RSS-first, HTML fallback)."""

from __future__ import annotations

import logging
from pathlib import Path

from bs4 import BeautifulSoup
from markdownify import markdownify as md

from convmd.core.download import process_images
from convmd.core.http import get_html
from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)


def convert_hatena(url: str, output_dir: Path) -> Path | None:
    html_text = get_html(url)
    if not html_text:
        return None

    soup = BeautifulSoup(html_text, "html.parser")
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else url

    entry = soup.select_one("div.entry-content, div.entry-body, article")
    if not entry:
        logger.warning(f"Could not find Hatena entry body at {url}")
        return None

    md_body = md(str(entry), heading_style="ATX")
    md_body = process_images(md_body, url, output_dir)
    frontmatter = generate_frontmatter(title, url, tags=["hatena", "blog"])

    path = output_dir / f"{sanitize_filename(title)}.md"
    path.write_text(frontmatter + md_body, encoding="utf-8")
    logger.info(f"Saved Hatena article to {path}")
    return path
