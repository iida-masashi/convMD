import logging
import re
from pathlib import Path
from typing import Any

import httpx

from convmd.core.download import process_images
from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)

def fetch_zenn_api(endpoint: str) -> Any | None:
    """Fetches data from Zenn's undocumented API (Next.js data)."""
    url = f"https://zenn.dev/api/{endpoint}"
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        with httpx.Client(follow_redirects=True, timeout=10.0) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch Zenn API {url}: {e}")
        return None

def convert_zenn_article(username: str, slug: str, output_dir: Path) -> Path | None:
    """Fetches a single Zenn article."""
    logger.info(f"Fetching Zenn article: {username}/{slug}")

    # Zenn exposes article data via articles API
    data = fetch_zenn_api(f"articles/{slug}")
    if not data or 'article' not in data:
        logger.error(f"Could not retrieve Zenn article: {slug}")
        return None

    article = data['article']
    title = article.get('title', 'Untitled')
    body = article.get('body_markdown', '') # Sometimes it's body_html, but API often provides markdown directly or we can get it via raw URL.

    url = f"https://zenn.dev/{username}/articles/{slug}"

    # If body_markdown is empty, we might need to fetch the raw GitHub-flavored markdown if available or fallback.
    # Fortunately, the api/articles/{slug} usually returns `body_markdown` or `body_html`.
    if not body and 'body_html' in article:
        from markdownify import markdownify as md
        body = md(article['body_html'], heading_style="ATX")

    if not body:
        logger.warning(f"No content found for Zenn article {slug}")
        body = "*No content could be extracted.*"

    tags = [t.get('name', '') for t in article.get('topics', [])]
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
    """Router for Zenn URLs."""
    # Pattern: https://zenn.dev/username/articles/slug
    article_match = re.search(r'zenn\.dev/([^/]+)/articles/([^/]+)', url)
    if article_match:
        return convert_zenn_article(article_match.group(1), article_match.group(2), output_dir)

    # NOTE: Scraping a user's entire publication list is harder on Zenn due to infinite scroll and complex API tokens.
    # We will stick to single articles for now.
    logger.warning("Zenn parser currently only supports individual article URLs (e.g., zenn.dev/user/articles/slug).")
    return None
