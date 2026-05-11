import logging
import re
from pathlib import Path
from typing import Any

import httpx

from convmd.core.download import process_images
from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)

def fetch_qiita_api(endpoint: str) -> Any | None:
    """Fetches data from Qiita API v2."""
    url = f"https://qiita.com/api/v2/{endpoint}"
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        with httpx.Client(follow_redirects=True, timeout=10.0) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            logger.error(f"Qiita API rate limit exceeded or access denied: {url}")
        else:
            logger.error(f"HTTP error {e.response.status_code} for {url}")
        return None
    except Exception as e:
        logger.error(f"Failed to fetch Qiita API {url}: {e}")
        return None

def convert_qiita_article(item_id: str, output_dir: Path) -> Path | None:
    """Fetches a single Qiita article and converts it to Markdown."""
    logger.info(f"Fetching Qiita article: {item_id}")
    data = fetch_qiita_api(f"items/{item_id}")

    if not data:
        return None

    title = data.get('title', 'Untitled')
    url = data.get('url', f"https://qiita.com/items/{item_id}")
    body = data.get('body', '')  # Qiita API returns raw markdown in 'body'
    tags = [t.get('name', '') for t in data.get('tags', [])]
    tags.append("qiita")

    # Although it's markdown, Qiita uses some HTML tags and external image links.
    # We download images to make it offline-friendly.
    logger.info("Processing images in Qiita article...")
    body = process_images(body, url, output_dir)

    frontmatter = generate_frontmatter(title, url, tags=[t for t in tags if t])

    filename = f"{sanitize_filename(title)}.md"
    file_path = output_dir / filename

    file_path.write_text(frontmatter + body, encoding="utf-8")
    logger.info(f"Saved Qiita article to {file_path}")

    return file_path

def convert_qiita_user(user_id: str, output_dir: Path) -> Path | None:
    """Fetches a user's recent articles from Qiita."""
    logger.info(f"Fetching Qiita articles for user: {user_id}")

    user_dir = output_dir / f"qiita_{sanitize_filename(user_id)}"
    user_dir.mkdir(parents=True, exist_ok=True)

    # Fetch up to 20 recent articles to avoid hitting rate limits too hard without a token
    items = fetch_qiita_api(f"items?query=user:{user_id}&per_page=20")

    if not items:
        logger.warning(f"No articles found for Qiita user {user_id}")
        return None

    logger.info(f"Found {len(items)} articles. Processing...")

    for item in items:
        item_id = item.get('id')
        if item_id:
            convert_qiita_article(item_id, user_dir)

    return user_dir

def convert_qiita(url: str, output_dir: Path) -> Path | None:
    """Router for Qiita URLs."""
    # Pattern: https://qiita.com/username/items/item_id
    item_match = re.search(r'qiita\.com/[^/]+/items/([a-zA-Z0-9]+)', url)
    if item_match:
        return convert_qiita_article(item_match.group(1), output_dir)

    # Pattern: https://qiita.com/username
    user_match = re.search(r'qiita\.com/([^/]+)/?$', url)
    if user_match:
        return convert_qiita_user(user_match.group(1), output_dir)

    logger.warning(f"Could not parse Qiita URL structure: {url}")
    return None
