"""Qiita article fetcher via Qiita API v2."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from convmd.core.download import process_images
from convmd.core.http import get_json
from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)


def fetch_qiita_api(endpoint: str) -> Any | None:
    return get_json(f"https://qiita.com/api/v2/{endpoint}")


def convert_qiita_article(item_id: str, output_dir: Path) -> Path | None:
    logger.info(f"Fetching Qiita article: {item_id}")
    data = fetch_qiita_api(f"items/{item_id}")
    if not data:
        return None

    title = data.get("title", "Untitled")
    url = data.get("url", f"https://qiita.com/items/{item_id}")
    body = data.get("body", "")
    tags = [t.get("name", "") for t in data.get("tags", [])]
    tags.append("qiita")

    logger.info("Processing images in Qiita article...")
    body = process_images(body, url, output_dir)

    frontmatter = generate_frontmatter(title, url, tags=[t for t in tags if t])

    filename = f"{sanitize_filename(title)}.md"
    file_path = output_dir / filename
    file_path.write_text(frontmatter + body, encoding="utf-8")
    logger.info(f"Saved Qiita article to {file_path}")
    return file_path


def convert_qiita_user(user_id: str, output_dir: Path) -> Path | None:
    logger.info(f"Fetching Qiita articles for user: {user_id}")
    user_dir = output_dir / f"qiita_{sanitize_filename(user_id)}"
    user_dir.mkdir(parents=True, exist_ok=True)

    items = fetch_qiita_api(f"items?query=user:{user_id}&per_page=20")
    if not items:
        logger.warning(f"No articles found for Qiita user {user_id}")
        return None

    logger.info(f"Found {len(items)} articles. Processing...")
    for item in items:
        item_id = item.get("id")
        if item_id:
            convert_qiita_article(item_id, user_dir)
    return user_dir


def convert_qiita(url: str, output_dir: Path) -> Path | None:
    item_match = re.search(r"qiita\.com/[^/]+/items/([a-zA-Z0-9]+)", url)
    if item_match:
        return convert_qiita_article(item_match.group(1), output_dir)

    user_match = re.search(r"qiita\.com/([^/]+)/?$", url)
    if user_match:
        return convert_qiita_user(user_match.group(1), output_dir)

    logger.warning(f"Could not parse Qiita URL structure: {url}")
    return None
