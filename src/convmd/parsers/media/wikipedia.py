"""Wikipedia article fetcher via REST API."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup
from markdownify import markdownify as md

from convmd.core.download import process_images
from convmd.core.http import get_html
from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)


def fetch_wikipedia_html(title: str, lang: str = "ja") -> str | None:
    # Wikipedia rejects both bare "Mozilla/5.0" and browser-spoofing UAs
    # for its REST API. Send a policy-compliant identifying UA per
    # https://meta.wikimedia.org/wiki/User-Agent_policy and hit the regular
    # article URL (the REST endpoint is even stricter).
    url = f"https://{lang}.wikipedia.org/wiki/{title}"
    return get_html(
        url,
        headers={"User-Agent": "convmd/0.1 (+https://github.com/iida-masashi/convMD)"},
    )


def clean_wikipedia_html(html_content: str) -> str:
    """Strip Wikipedia UI chrome (edit links, references, navboxes) before MD conversion."""
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup.select(
        ".mw-editsection, .reference, .navbox, .metadata, .infobox, .sistersitebox"
    ):
        tag.decompose()
    return str(soup)


def convert_wikipedia(url: str, output_dir: Path) -> Path | None:
    parsed_url = urlparse(url)
    lang_match = re.match(r"^([a-z\-]+)\.wikipedia\.org$", parsed_url.netloc)
    lang = lang_match.group(1) if lang_match else "en"

    path_parts = parsed_url.path.strip("/").split("/")
    if len(path_parts) < 2 or path_parts[0] != "wiki":
        logger.warning(f"Invalid Wikipedia URL structure: {url}")
        return None

    article_title_raw = path_parts[1]
    logger.info(f"Fetching Wikipedia article: {unquote(article_title_raw)} ({lang})")

    html = fetch_wikipedia_html(article_title_raw, lang)
    if not html:
        return None

    display_title = unquote(article_title_raw).replace("_", " ")

    cleaned_html = clean_wikipedia_html(html)
    md_body = md(
        cleaned_html, heading_style="ATX", escape_asterisks=False, escape_underscores=False
    )
    md_body = process_images(md_body, f"https://{lang}.wikipedia.org", output_dir)

    frontmatter = generate_frontmatter(display_title, url, tags=["wikipedia", lang])

    filename = f"{sanitize_filename(display_title)}.md"
    file_path = output_dir / filename
    file_path.write_text(frontmatter + md_body, encoding="utf-8")
    logger.info(f"Saved Wikipedia article to {file_path}")
    return file_path
