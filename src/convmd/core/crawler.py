"""Same-domain BFS crawler used by --depth option."""

from __future__ import annotations

import logging
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from convmd.constants import CRAWL_TIMEOUT, USER_AGENT
from convmd.core.http import _verify_default

logger = logging.getLogger(__name__)


def crawl_urls(start_url: str, max_depth: int) -> list[str]:
    """BFS crawl restricted to the same domain. Depth 0 returns ``[start_url]`` only."""
    if max_depth <= 0:
        return [start_url]

    visited: set[str] = set()
    queue: list[tuple[str, int]] = [(start_url, 0)]
    results: list[str] = []
    base_domain = urlparse(start_url).netloc

    with httpx.Client(
        follow_redirects=True, timeout=CRAWL_TIMEOUT, verify=_verify_default()
    ) as client:
        while queue:
            current_url, current_depth = queue.pop(0)
            parsed_current = urlparse(current_url)
            normalized_url = parsed_current._replace(fragment="").geturl()

            if normalized_url in visited:
                continue
            visited.add(normalized_url)
            results.append(normalized_url)

            if current_depth >= max_depth:
                continue

            logger.info(f"Crawling (Depth {current_depth}/{max_depth}): {normalized_url}")
            try:
                response = client.get(normalized_url, headers={"User-Agent": USER_AGENT})
                if response.status_code != 200 or "text/html" not in response.headers.get(
                    "Content-Type", ""
                ):
                    continue

                soup = BeautifulSoup(response.content, "html.parser")
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    if isinstance(href, list):
                        href = href[0]
                    full_url = urljoin(normalized_url, str(href))
                    parsed_full = urlparse(full_url)
                    if (
                        parsed_full.scheme in ("http", "https")
                        and parsed_full.netloc == base_domain
                    ):
                        queue.append((full_url, current_depth + 1))

            except Exception as e:
                logger.warning(f"Failed to crawl {normalized_url}: {e}")

    logger.info(f"Crawling complete. Found {len(results)} URLs within depth {max_depth}.")
    return results
