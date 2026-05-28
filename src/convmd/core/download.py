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

from convmd.constants import DEFAULT_TIMEOUT, DOWNLOAD_TIMEOUT, USER_AGENT
from convmd.core.http import _verify_default, encode_url_path

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


def fetch_html(url: str) -> str | None:
    """Fetch HTML content from a URL with safe path encoding and charset fallback."""
    encoded_url = encode_url_path(url)
    try:
        with httpx.Client(
            follow_redirects=True, timeout=DEFAULT_TIMEOUT, verify=_verify_default()
        ) as client:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            response = client.get(encoded_url, headers=headers)
            response.raise_for_status()
            charset = _detect_html_charset(response.content, response.charset_encoding)
            return response.content.decode(charset, errors="replace")
    except httpx.RequestError as e:
        logger.error(f"Failed to request {url}: {e}")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error {e.response.status_code} for {url}")
        return None


_IMG_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def process_images(md_content: str, base_url: str, output_dir: Path) -> str:
    """Replace remote Markdown image URLs with local downloads under ``output_dir/images``."""
    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    def replace_img(match: re.Match) -> str:
        alt_text = match.group(1)
        img_url = match.group(2)

        if img_url.startswith("data:"):
            return str(match.group(0))

        if not img_url.startswith("http"):
            img_url = urljoin(base_url, img_url)

        try:
            parsed_url = urlparse(img_url)
            filename = Path(urllib.parse.unquote(parsed_url.path)).name
            if not filename or "." not in filename:
                filename = f"image_{hash(img_url) % 100000000:08d}.jpg"

            filename = re.sub(r'[\\/*?:"<>|]', "", filename)
            local_img_path = image_dir / filename

            unquoted_path = urllib.parse.unquote(parsed_url.path)
            encoded_path = urllib.parse.quote(unquoted_path)
            safe_img_url = parsed_url._replace(path=encoded_path).geturl()

            if not local_img_path.exists():
                with httpx.Client(
                    follow_redirects=True,
                    timeout=DOWNLOAD_TIMEOUT,
                    verify=_verify_default(),
                ) as client:
                    response = client.get(safe_img_url, headers={"User-Agent": USER_AGENT})
                    response.raise_for_status()
                    local_img_path.write_bytes(response.content)

            return f"![{alt_text}](images/{filename})"

        except Exception as e:
            logger.warning(f"Failed to download image {img_url}: {e}")
            return str(match.group(0))

    return _IMG_PATTERN.sub(replace_img, md_content)
