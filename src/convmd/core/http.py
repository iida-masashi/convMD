"""Centralized HTTP helpers.

All outbound HTTP in convmd should funnel through here so that:
- TLS verification policy is configured in one place (env-toggle for legacy hosts).
- The User-Agent and timeout defaults are consistent.
- URL path encoding is applied uniformly.
"""

from __future__ import annotations

import logging
import os
import random
import re
import time
import urllib.parse
from pathlib import Path
from typing import Any, Callable, Mapping, TypeVar

import httpx

from convmd.constants import DEFAULT_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)

# Internal reliability tuning, not user-facing (no CLI flags).
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BASE_DELAY = 0.5
_RETRYABLE_STATUS_CODES = {429}  # plus any 5xx, checked separately

_RETRYABLE_EXCEPTIONS = (httpx.TimeoutException, httpx.ConnectError, httpx.ConnectTimeout)

T = TypeVar("T")


def _is_retryable_status_error(e: httpx.HTTPStatusError) -> bool:
    status = e.response.status_code
    return status in _RETRYABLE_STATUS_CODES or status >= 500


def _request_with_retry(
    attempt_fn: Callable[[], T],
    *,
    url: str,
    max_retries: int = _DEFAULT_MAX_RETRIES,
    base_delay: float = _DEFAULT_BASE_DELAY,
) -> T:
    """Run ``attempt_fn`` with exponential backoff on transient failures.

    Retries on network timeouts/connection errors and on 429/5xx HTTP status
    errors. Any other exception (including 4xx status errors) propagates
    immediately on the first attempt. On final failure, the last exception
    is re-raised so callers' existing except-blocks handle logging/return
    values unchanged.
    """
    for attempt in range(max_retries + 1):
        reason: Exception
        try:
            return attempt_fn()
        except _RETRYABLE_EXCEPTIONS as e:
            reason = e
        except httpx.HTTPStatusError as e:
            if not _is_retryable_status_error(e):
                raise
            reason = e

        if attempt == max_retries:
            raise reason

        delay = base_delay * (2**attempt) + random.uniform(0, base_delay * 0.1)
        logger.warning(f"Retry {attempt + 1}/{max_retries} for {url} after error: {reason}")
        time.sleep(delay)

    raise AssertionError("unreachable")  # loop always returns or raises above


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
    max_retries: int = _DEFAULT_MAX_RETRIES,
    base_delay: float = _DEFAULT_BASE_DELAY,
) -> Any | None:
    """GET a URL and return parsed JSON, or None on any failure."""

    def _attempt() -> httpx.Response:
        with get_client(timeout=timeout) as client:
            response = client.get(url, headers=_default_headers(headers))
            response.raise_for_status()
            return response

    try:
        response = _request_with_retry(
            _attempt, url=url, max_retries=max_retries, base_delay=base_delay
        )
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
    """GET a URL and return fully rendered HTML using Playwright.

    Falls back to browser4-cli (a separately installed Node.js CLI, see
    ``core/browser4.py``) if Playwright is missing or fails to render the page.
    """
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
        logger.error("Playwright not installed. Falling back to browser4-cli if available.")
        return _get_html_with_browser4_fallback(url, timeout)
    except Exception as e:
        logger.error(f"Playwright failed for {url}: {e}. Falling back to browser4-cli if available.")
        return _get_html_with_browser4_fallback(url, timeout)


def _get_html_with_browser4_fallback(url: str, timeout: float) -> str | None:
    from convmd.core.browser4 import get_html_with_browser4, is_available

    if not is_available():
        logger.error("browser4-cli not found on PATH. Install via 'npm install -g browser4-cli'.")
        return _get_html_with_firecrawl_fallback(url, timeout)

    html = get_html_with_browser4(url, timeout=timeout)
    if html:
        return html
    return _get_html_with_firecrawl_fallback(url, timeout)


def _get_html_with_firecrawl_fallback(url: str, timeout: float) -> str | None:
    from convmd.core.firecrawl_fallback import get_html_with_firecrawl, is_available

    if not is_available():
        logger.error(f"FIRECRAWL_API_KEY not set; no rendering fallback left for {url}.")
        return None
    return get_html_with_firecrawl(url, timeout=timeout)


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
    max_retries: int = _DEFAULT_MAX_RETRIES,
    base_delay: float = _DEFAULT_BASE_DELAY,
) -> str | None:
    """GET a URL and decode response text safely with charset fallback.

    Extra ``headers`` are merged into the default headers (notably overriding
    ``User-Agent`` for sites like Wikipedia that reject the default UA).
    """
    if render_js:
        logger.info(f"Using Playwright for explicit JS rendering: {url}")
        return get_html_with_js(url, timeout=timeout)

    encoded_url = encode_url_path(url)

    def _attempt() -> httpx.Response:
        with get_client(timeout=timeout) as client:
            response = client.get(encoded_url, headers=_default_headers(headers))
            response.raise_for_status()
            return response

    try:
        response = _request_with_retry(
            _attempt, url=url, max_retries=max_retries, base_delay=base_delay
        )
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


def download_binary(
    url: str,
    dest: Path,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = _DEFAULT_MAX_RETRIES,
    base_delay: float = _DEFAULT_BASE_DELAY,
) -> bool:
    """GET a URL and stream the body to ``dest``. Returns True on success."""
    encoded_url = encode_url_path(url)

    def _attempt() -> None:
        with get_client(timeout=timeout) as client:
            with client.stream("GET", encoded_url, headers=_default_headers()) as response:
                response.raise_for_status()
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open("wb") as fh:
                    for chunk in response.iter_bytes():
                        fh.write(chunk)

    try:
        _request_with_retry(_attempt, url=url, max_retries=max_retries, base_delay=base_delay)
        return True
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error {e.response.status_code} downloading {url}")
        return False
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return False
