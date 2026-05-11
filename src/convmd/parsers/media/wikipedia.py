import logging
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from convmd.core.download import process_images
from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)

def fetch_wikipedia_api(title: str, lang: str = "ja") -> dict | None:
    """Fetches article content using Wikipedia REST API."""
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/html/{title}"
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        with httpx.Client(follow_redirects=True, timeout=10.0) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            # Wikipedia REST API returns raw HTML
            return {"html": response.text, "title": title}
    except Exception as e:
        logger.error(f"Failed to fetch Wikipedia API for {title}: {e}")
        return None

def clean_wikipedia_html(html_content: str) -> str:
    """Removes unwanted Wikipedia UI elements (edit links, references, etc.) before markdown conversion."""
    soup = BeautifulSoup(html_content, 'html.parser')

    # Remove edit links, reference superscripts, navboxes, etc.
    for tag in soup.select('.mw-editsection, .reference, .navbox, .metadata, .infobox, .sistersitebox'):
        tag.decompose()

    # Wikipedia REST API adds some section wrappers we might want to keep or unwrap
    return str(soup)

def convert_wikipedia(url: str, output_dir: Path) -> Path | None:
    """Fetches a Wikipedia article and converts it to clean Markdown."""
    parsed_url = urlparse(url)
    # Extract language sub-domain (e.g., 'ja' from 'ja.wikipedia.org')
    lang_match = re.match(r'^([a-z\-]+)\.wikipedia\.org$', parsed_url.netloc)
    lang = lang_match.group(1) if lang_match else "en"

    # Extract the article title from the path
    # e.g., /wiki/%E6%97%A5%E6%9C%AC -> 日本
    path_parts = parsed_url.path.strip('/').split('/')
    if len(path_parts) < 2 or path_parts[0] != 'wiki':
        logger.warning(f"Invalid Wikipedia URL structure: {url}")
        return None

    article_title_raw = path_parts[1]

    logger.info(f"Fetching Wikipedia article: {unquote(article_title_raw)} ({lang})")
    data = fetch_wikipedia_api(article_title_raw, lang)

    if not data:
        return None

    display_title = unquote(article_title_raw).replace('_', ' ')

    logger.info("Cleaning Wikipedia HTML...")
    cleaned_html = clean_wikipedia_html(data['html'])

    logger.info("Converting to Markdown...")
    md_body = md(cleaned_html, heading_style="ATX", escape_asterisks=False, escape_underscores=False)

    logger.info("Processing images...")
    # Wikipedia REST API often uses relative protocol like //upload.wikimedia.org/...
    # process_images usually handles relative links, but let's ensure base_url is full
    md_body = process_images(md_body, f"https://{lang}.wikipedia.org", output_dir)

    frontmatter = generate_frontmatter(display_title, url, tags=["wikipedia", lang])

    filename = f"{sanitize_filename(display_title)}.md"
    file_path = output_dir / filename

    file_path.write_text(frontmatter + md_body, encoding="utf-8")
    logger.info(f"Saved Wikipedia article to {file_path}")

    return file_path
