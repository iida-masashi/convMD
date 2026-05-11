"""Centralized HTTP helpers.

All outbound HTTP in convmd should funnel through here so that:
- TLS verification policy is configured in one place (env-toggle for legacy hosts).
- The User-Agent and timeout defaults are consistent.
- URL path encoding is applied uniformly.
"""

from __future__ import annotations

import logging
import os
import urllib.parse
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


def encode_url_path(url: str) -> str:
    """Idempotently percent-encode the path component (used to be in download.fetch_html)."""
    parsed = urllib.parse.urlparse(url)
    unquoted_path = urllib.parse.unquote(parsed.path)
    encoded_path = urllib.parse.quote(unquoted_path)
    return parsed._replace(path=encoded_path).geturl()


def get_html(url: str, *, timeout: float = DEFAULT_TIMEOUT) -> str | None:
    """GET a URL and decode response text safely with charset fallback."""
    encoded_url = encode_url_path(url)
    try:
        with get_client(timeout=timeout) as client:
            response = client.get(encoded_url, headers=_default_headers())
            response.raise_for_status()
            charset = response.encoding or "utf-8"
            return response.content.decode(charset, errors="replace")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error {e.response.status_code} for {url}")
        return None
    except Exception as e:
        logger.error(f"Failed to request {url}: {e}")
        return None
