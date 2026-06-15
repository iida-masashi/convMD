"""Centralized HTTP helpers.

All outbound HTTP in convmd should funnel through here so that:
- TLS verification policy is configured in one place (env-toggle for legacy hosts).
- The User-Agent and timeout defaults are consistent.
- URL path encoding is applied uniformly.
"""

from __future__ import annotations

import logging
import os
import re
import urllib.parse
from pathlib import Path
from typing import Any, Mapping

import httpx

from convmd.constants import DEFAULT_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)


def _verify_default() -> bool:
    """Return TLS verify policy. Default True, overridable via CONVMD_INSECURE_SSL=1."""
    return os.environ.get("CONVMD_INSECURE_SSL", "").lower() not in {"1", "true", "yes"}


def get_client(
    *,
    timeout: float = DEFAULT_TIMEOUT,
    verify: bool | None = None,
    follow_redirects: bool = True,
) -> httpx.Client:
    """Build a configured httpx.Client. Caller is responsible for ``with`` lifecycle."""
    return httpx.Client(
        follow_redirects=follow_redirects,
        timeout=timeout,
        verify=_verify_default() if verify is None else verify,
    )


def _default_headers(extra: Mapping[str, str] | None = None) -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT}
    if extra:
        headers.update(extra)
    return headers


def get_json(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    headers: Mapping[str, str] | None = None,
) -> Any | None:
    """GET a URL and return parsed JSON, or None on any failure."""
    try:
        with get_client(timeout=timeout) as client:
            response = client.get(url, headers=_default_headers(headers))
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error {e.response.status_code} for {url}")
        return None
    except Exception as e:
        logger.error(f"Failed to fetch JSON from {url}: {e}")
        return None


_CHARSET_RE = re.compile(r"""charset=["']?([\w-]+)""", re.IGNORECASE)


def _resolve_charset(content_type: str, body: bytes) -> str:
    """Resolve the response charset: HTTP header first, then <meta>, else utf-8.

    httpx defaults ``response.encoding`` to utf-8 when the header omits a charset,
    which mojibakes legacy pages that declare their charset only in a ``<meta>``
    tag (e.g. ISO-2022-JP). Honor the declared charset with standard precedence.
    """
    m = _CHARSET_RE.search(content_type)
    if m:
        return m.group(1)
    head = body[:2048].decode("latin-1", errors="replace")
    m = _CHARSET_RE.search(head)
    return m.group(1) if m else "utf-8"


def encode_url_path(url: str) -> str:
    """Idempotently percent-encode the path component (used to be in download.fetch_html)."""
    parsed = urllib.parse.urlparse(url)
    unquoted_path = urllib.parse.unquote(parsed.path)
    encoded_path = urllib.parse.quote(unquoted_path)
    return parsed._replace(path=encoded_path).geturl()


def get_html_with_js(url: str, timeout: float = DEFAULT_TIMEOUT) -> str | None:
    """GET a URL and return fully rendered HTML using Playwright."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()
            encoded_url = encode_url_path(url)
            page.goto(encoded_url, wait_until="networkidle", timeout=int(timeout * 1000))
            content = page.content()
            browser.close()
            return content
    except ImportError:
        logger.error("Playwright not installed. Run 'uv add playwright' to use --render-js.")
        return None
    except Exception as e:
        logger.error(f"Playwright failed for {url}: {e}")
        return None


def is_spa_empty(html: str) -> bool:
    """Heuristic to detect if the HTML is an empty SPA shell or highly JS-dependent."""
    # Very short HTML is suspicious
    if len(html) < 1000:
        return True

    import re

    # Check for known SPA framework signatures
    if (
        re.search(r'id="__nuxt"', html)
        or re.search(r'id="__next"', html)
        or re.search(r"window\.__NUXT__", html)
    ):
        return True

    # Check for common SPA root tags with very little content inside
    body_content = re.search(r"<body[^>]*>(.*?)</body>", html, re.IGNORECASE | re.DOTALL)
    if body_content:
        # Strip script tags inside body to see real content length
        real_content = re.sub(
            r"<script[^>]*>.*?</script>", "", body_content.group(1), flags=re.IGNORECASE | re.DOTALL
        )
        # Strip noscript tags
        real_content = re.sub(
            r"<noscript[^>]*>.*?</noscript>", "", real_content, flags=re.IGNORECASE | re.DOTALL
        )
        # Strip generic div/span tags to see if there's actual text
        text_content = re.sub(r"<[^>]+>", "", real_content)
        if len(text_content.strip()) < 500:
            return True

    return False


def get_html(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    headers: Mapping[str, str] | None = None,
    render_js: bool = False,
) -> str | None:
    """GET a URL and decode response text safely with charset fallback.

    Extra ``headers`` are merged into the default headers (notably overriding
    ``User-Agent`` for sites like Wikipedia that reject the default UA).
    """
    if render_js:
        logger.info(f"Using Playwright for explicit JS rendering: {url}")
        return get_html_with_js(url, timeout=timeout)

    encoded_url = encode_url_path(url)
    try:
        with get_client(timeout=timeout) as client:
            response = client.get(encoded_url, headers=_default_headers(headers))
            response.raise_for_status()
            charset = _resolve_charset(response.headers.get("content-type", ""), response.content)
            try:
                html = response.content.decode(charset, errors="replace")
            except LookupError:
                html = response.content.decode("utf-8", errors="replace")

            # Auto-detect SPA
            if is_spa_empty(html):
                logger.info(
                    f"Auto-detected SPA shell for {url}. Falling back to Playwright rendering..."
                )
                js_html = get_html_with_js(url, timeout=timeout)
                return js_html if js_html else html

            return html
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error {e.response.status_code} for {url}")
        return None
    except Exception as e:
        logger.error(f"Failed to request {url}: {e}")
        return None


def download_binary(url: str, dest: Path, *, timeout: float = DEFAULT_TIMEOUT) -> bool:
    """GET a URL and stream the body to ``dest``. Returns True on success."""
    encoded_url = encode_url_path(url)
    try:
        with get_client(timeout=timeout) as client:
            with client.stream("GET", encoded_url, headers=_default_headers()) as response:
                response.raise_for_status()
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open("wb") as fh:
                    for chunk in response.iter_bytes():
                        fh.write(chunk)
        return True
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error {e.response.status_code} downloading {url}")
        return False
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return False
