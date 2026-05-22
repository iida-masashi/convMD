"""SpeakerDeck slide deck fetcher — downloads each slide image and OCRs it."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from bs4 import BeautifulSoup

from convmd.core import gemini
from convmd.core.http import get_html
from convmd.core.iiif import download_image
from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)


_OG_IMG_RE = re.compile(r'<meta\s+property="og:image"\s+content="([^"]+)"')


def _slide_image_urls(html: str) -> list[str]:
    """Extract all slide image URLs from a SpeakerDeck page."""
    urls: list[str] = []
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.select("img[data-src], img[src]"):
        raw = img.get("data-src") or img.get("src")
        if not raw:
            continue
        src = str(raw)
        if "speakerdeck" not in src and "files.speakerdeck.com" not in src:
            continue
        if any(seg in src for seg in ("slide_", "/slides/")):
            urls.append(src)
    if urls:
        return urls

    og_match = _OG_IMG_RE.search(html)
    if og_match:
        urls.append(og_match.group(1))
    return urls


def convert_speakerdeck(url: str, output_dir: Path) -> Path | None:
    html = get_html(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else url

    slide_urls = _slide_image_urls(html)
    if not slide_urls:
        logger.warning(f"No slide images found at {url}")
        return None

    deck_dir = output_dir / sanitize_filename(title)
    image_dir = deck_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    body_parts: list[str] = [
        generate_frontmatter(title, url, tags=["speakerdeck", "slides"]),
        f"# {title}\n\n",
    ]

    do_ocr = gemini.is_configured()
    for i, img_url in enumerate(slide_urls, start=1):
        img_name = f"slide_{i:04d}.jpg"
        img_path = image_dir / img_name
        try:
            download_image(img_url, img_path)
        except Exception as e:
            logger.warning(f"Failed to download slide {i}: {e}")
            continue
        body_parts.append(f"\n## Slide {i}\n\n![[images/{img_name}]]\n\n")
        if do_ocr:
            text = gemini.transcribe_image(img_path)
            if text:
                body_parts.append("> " + text.replace("\n", "\n> ") + "\n\n")

    md_path = deck_dir / f"{sanitize_filename(title)}.md"
    md_path.write_text("".join(body_parts), encoding="utf-8")
    logger.info(f"Saved SpeakerDeck content to {md_path}")
    return md_path
