"""Zenn (zenn.dev) article fetcher via the site's undocumented Next.js data API."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from convmd.core.download import process_images
from convmd.core.http import get_json
from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)


def fetch_zenn_api(endpoint: str) -> Any | None:
    return get_json(f"https://zenn.dev/api/{endpoint}")


def convert_zenn_article(username: str, slug: str, output_dir: Path) -> Path | None:
    logger.info(f"Fetching Zenn article: {username}/{slug}")

    data = fetch_zenn_api(f"articles/{slug}")
    if not data or "article" not in data:
        logger.error(f"Could not retrieve Zenn article: {slug}")
        return None

    article = data["article"]
    title = article.get("title", "Untitled")
    body = article.get("body_markdown", "")
    url = f"https://zenn.dev/{username}/articles/{slug}"

    if not body and "body_html" in article:
        from markdownify import markdownify as md

        body = md(article["body_html"], heading_style="ATX")

    if not body:
        logger.warning(f"No content found for Zenn article {slug}")
        body = "*No content could be extracted.*"

    tags = [t.get("name", "") for t in article.get("topics", [])]
    tags.append("zenn")

    logger.info("Processing images in Zenn article...")
    body = process_images(body, url, output_dir)

    frontmatter = generate_frontmatter(title, url, tags=[t for t in tags if t])

    filename = f"{sanitize_filename(title)}.md"
    file_path = output_dir / filename
    file_path.write_text(frontmatter + body, encoding="utf-8")
    logger.info(f"Saved Zenn article to {file_path}")
    return file_path


def convert_zenn(url: str, output_dir: Path) -> Path | None:
    """Router for Zenn URLs (currently supports individual article URLs)."""
    article_match = re.search(r"zenn\.dev/([^/]+)/articles/([^/]+)", url)
    if article_match:
        return convert_zenn_article(article_match.group(1), article_match.group(2), output_dir)

    logger.warning(
        "Zenn parser currently only supports individual article URLs (e.g., zenn.dev/user/articles/slug)."
    )
    return None
