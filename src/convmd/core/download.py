"""Legacy facade for HTML fetching and image downloading.

The actual centralized helpers now live in ``convmd.core.http``. This module
remains so existing imports (and unit tests patching ``convmd.core.download.httpx.Client``)
continue to work without churn.
"""

from __future__ import annotations

import codecs
import logging
import re
import urllib.parse
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

from convmd.constants import DOWNLOAD_TIMEOUT, USER_AGENT
from convmd.core.http import _verify_default

logger = logging.getLogger(__name__)


_META_CHARSET_RE = re.compile(
    rb"""<meta[^>]+charset\s*=\s*["']?([\w\-]+)""", re.IGNORECASE
)


def _is_valid_codec(name: str) -> bool:
    """Return True iff ``name`` resolves to a real Python codec.

    Guards against bogus meta declarations like ``<meta charset="unicode">`` —
    ``bytes.decode(name, errors="replace")`` raises ``LookupError`` for unknown
    codec names (the ``errors`` kwarg only rescues malformed bytes, not lookup).
    """
    try:
        codecs.lookup(name)
        return True
    except LookupError:
        return False


def _detect_html_charset(content: bytes, http_charset: str | None) -> str:
    """Resolve charset from HTML meta tag, then HTTP header, then fallbacks.

    httpx returns ISO-8859-1 when the HTTP header has no charset, which mangles
    Shift_JIS / EUC-JP pages. Prefer the in-document declaration.
    """
    m = _META_CHARSET_RE.search(content[:4096])
    if m:
        candidate = m.group(1).decode("ascii", errors="ignore")
        if candidate and _is_valid_codec(candidate):
            return candidate
    if http_charset and http_charset.lower() not in {"iso-8859-1", "ascii"} and _is_valid_codec(
        http_charset
    ):
        return http_charset
    # Try utf-8 first; if it fails, fall back to cp932 (Windows Japanese).
    try:
        content.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "cp932"


def fetch_html(url: str, render_js: bool = False) -> str | None:
    """Fetch HTML content from a URL with safe path encoding and charset fallback."""
    from convmd.core.http import get_html
    return get_html(url, render_js=render_js)


_IMG_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def _prepare_image_target(
    raw_url: str, base_url: str, image_dir: Path
) -> tuple[str, str, Path, str] | None:
    """Resolve a Markdown image URL to ``(resolved_url, filename, local_path, safe_url)``."""
    if raw_url.startswith("data:"):
        return None
    img_url = raw_url if raw_url.startswith("http") else urljoin(base_url, raw_url)
    parsed_url = urlparse(img_url)
    filename = Path(urllib.parse.unquote(parsed_url.path)).name
    if not filename or "." not in filename:
        filename = f"image_{hash(img_url) % 100000000:08d}.jpg"
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    local_img_path = image_dir / filename
    unquoted_path = urllib.parse.unquote(parsed_url.path)
    encoded_path = urllib.parse.quote(unquoted_path)
    safe_img_url = parsed_url._replace(path=encoded_path).geturl()
    return img_url, filename, local_img_path, safe_img_url


def _download_single_image(img_url: str, safe_img_url: str, local_img_path: Path) -> bool:
    if local_img_path.exists():
        return True
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=DOWNLOAD_TIMEOUT,
            verify=_verify_default(),
        ) as client:
            response = client.get(safe_img_url, headers={"User-Agent": USER_AGENT})
            response.raise_for_status()
            local_img_path.write_bytes(response.content)
        return True
    except Exception as e:
        logger.warning(f"Failed to download image {img_url}: {e}")
        return False


def process_images(
    md_content: str, base_url: str, output_dir: Path, *, max_workers: int = 4
) -> str:
    """Replace remote Markdown image URLs with local downloads under ``output_dir/images``."""
    from concurrent.futures import ThreadPoolExecutor

    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    # Deduplicate image targets across the document
    targets: dict[str, tuple[str, str, Path, str]] = {}
    for match in _IMG_PATTERN.finditer(md_content):
        raw_url = match.group(2)
        if raw_url not in targets:
            try:
                prepared = _prepare_image_target(raw_url, base_url, image_dir)
                if prepared is not None:
                    targets[raw_url] = prepared
            except Exception as e:
                logger.warning(f"Failed to download image {raw_url}: {e}")

    status_by_raw_url: dict[str, str] = {}
    items = list(targets.items())
    if len(items) <= 1 or max_workers <= 1:
        for raw_url, (img_url, filename, local_path, safe_url) in items:
            if _download_single_image(img_url, safe_url, local_path):
                status_by_raw_url[raw_url] = filename
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                raw_url: (
                    filename,
                    executor.submit(_download_single_image, img_url, safe_url, local_path),
                )
                for raw_url, (img_url, filename, local_path, safe_url) in items
            }
            for raw_url, (filename, fut) in futures.items():
                if fut.result():
                    status_by_raw_url[raw_url] = filename

    def replace_img(match: re.Match[str]) -> str:
        alt_text = match.group(1)
        raw_url = match.group(2)
        filename = status_by_raw_url.get(raw_url)
        if filename is not None:
            return f"![{alt_text}](images/{filename})"
        return str(match.group(0))

    return _IMG_PATTERN.sub(replace_img, md_content)
