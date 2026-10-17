from __future__ import annotations

import logging
import re
from pathlib import Path
from urllib.parse import urlparse

import trafilatura  # type: ignore[import-untyped]
from markdownify import markdownify as md
from readability import Document  # type: ignore[import-untyped]

from convmd.core.download import fetch_html, process_images
from convmd.core.utils import (
    body_text,
    generate_frontmatter,
    sanitize_filename,
    unique_output_path,
)

logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(
    r"<(?:!doctype|html|head|body|div|article|main|section|p|h[1-6]|table|span)\b",
    re.IGNORECASE,
)
_MD_HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_FM_TITLE_RE = re.compile(r'^title:\s*["\']?(.*?)["\']?\s*$', re.MULTILINE)


def _looks_like_markdown(content: str) -> bool:
    """Return True when the payload has no common HTML structure tags."""
    return not bool(_HTML_TAG_RE.search(content[:4096]))


def _extract_markdown_title(md_text: str, url: str) -> str:
    """Extract a title from frontmatter, first H1 heading, or URL hostname."""
    if md_text.lstrip().startswith("---"):
        end = md_text.find("\n---", 3)
        if end != -1:
            fm_match = _FM_TITLE_RE.search(md_text[: end + 4])
            if fm_match and fm_match.group(1).strip():
                return fm_match.group(1).strip()
    h1_match = _MD_HEADING_RE.search(md_text)
    if h1_match and h1_match.group(1).strip():
        return h1_match.group(1).strip()
    return urlparse(url).netloc or "Untitled"


def _extract_with_trafilatura(
    html: str, url: str
) -> tuple[str | None, str | None, str | None, str | None]:
    """Attempt Tier 1 extraction with trafilatura.

    Returns ``(markdown_body, title, author, published_at)``.
    """
    try:
        extracted: str | None = trafilatura.extract(
            html,
            output_format="markdown",
            include_tables=True,
            include_links=True,
            include_images=True,
            url=url,
        )
        meta = trafilatura.extract_metadata(html, default_url=url)
        title = getattr(meta, "title", None) if meta else None
        author = getattr(meta, "author", None) if meta else None
        published_at = getattr(meta, "date", None) if meta else None
        return extracted, title, author, published_at
    except Exception as e:
        logger.debug(f"Trafilatura extraction failed for {url}: {e}")
        return None, None, None, None


def _extract_with_readability(html: str) -> tuple[str, str]:
    """Tier 2 fallback extraction using Readability + markdownify."""
    doc = Document(html)
    title = str(doc.title() or "")
    summary_html = doc.summary()
    md_body = str(md(summary_html, heading_style="ATX"))
    return md_body, title


def convert_general_website(url: str, output_dir: Path, render_js: bool = False) -> Path | None:
    """Fetch a general URL, extract main content via Trafilatura (with Readability
    fallback), and save it as a Markdown file with local images.
    """
    logger.info(f"Processing {url} with general web engine...")
    raw_content = fetch_html(url, render_js=render_js)
    if not raw_content:
        logger.error(f"Failed to retrieve content for {url}")
        return None

    author: str | None = None
    published_at: str | None = None

    if _looks_like_markdown(raw_content):
        logger.info(f"Detected direct Markdown response for {url}")
        title = _extract_markdown_title(raw_content, url)
        md_body = body_text(raw_content)
    else:
        extracted, traf_title, author, published_at = _extract_with_trafilatura(raw_content, url)
        if extracted and len(extracted.strip()) >= 100:
            md_body = extracted
            if traf_title:
                title = traf_title
            else:
                try:
                    title = str(Document(raw_content).title() or "")
                except Exception:
                    title = ""
            if not title:
                title = _extract_markdown_title(md_body, url)
        else:
            logger.info(f"Falling back to Readability engine for {url}...")
            md_body, title = _extract_with_readability(raw_content)

    # Download images and update links
    logger.info("Downloading images and updating links...")
    md_body = process_images(md_body, url, output_dir)

    # If the extracted body is extremely short, return None to trigger AI fallback in routing.py
    if len(md_body.strip()) < 100:
        logger.warning(
            f"Extracted very little content ({len(md_body.strip())} bytes) for {url}. "
            "Returning None to trigger AI fallback."
        )
        return None

    # Generate frontmatter
    frontmatter = generate_frontmatter(
        title,
        url,
        tags=["web_clip", "general"],
        author=author,
        published_at=published_at,
    )

    # Generate filename and path
    safe_title = sanitize_filename(title)
    file_path = unique_output_path(output_dir, safe_title, url)

    # Save the file
    file_path.write_text(frontmatter + md_body, encoding="utf-8")

    logger.info(f"Saved to {file_path}")
    return file_path
