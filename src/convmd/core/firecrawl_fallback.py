"""Thin wrapper around the Firecrawl API (https://github.com/firecrawl/firecrawl).

Used only as a last-resort fallback when Playwright and browser4-cli have both
failed or are unavailable — see ``core.http.get_html_with_js``. Not a
general-purpose Firecrawl client (no crawl/map/extract support here).
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def is_available() -> bool:
    """True iff a Firecrawl API key is configured."""
    return bool(os.environ.get("FIRECRAWL_API_KEY"))


def get_html_with_firecrawl(url: str, timeout: float) -> str | None:
    """Render ``url`` via the Firecrawl API and return the raw HTML, or None on failure."""
    try:
        from firecrawl import Firecrawl  # type: ignore
    except ImportError:
        logger.error("firecrawl-py not installed. Install via 'uv sync --extra firecrawl'.")
        return None

    try:
        client = Firecrawl()
        doc = client.scrape(url, formats=["rawHtml"], timeout=int(timeout))
        if doc.raw_html:
            return str(doc.raw_html)
        logger.error(f"Firecrawl returned no HTML for {url}")
        return None
    except Exception as e:
        logger.error(f"Firecrawl failed for {url}: {e}")
        return None
