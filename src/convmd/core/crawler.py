import logging
from typing import List, Set
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def crawl_urls(start_url: str, max_depth: int) -> List[str]:
    """
    Crawls starting from start_url up to max_depth, returning a list of unique URLs within the same domain.
    Depth 0 returns just [start_url].
    Depth 1 returns [start_url, ...links_found_on_start_url].
    """
    if max_depth <= 0:
        return [start_url]

    visited: Set[str] = set()
    queue = [(start_url, 0)]
    results: List[str] = []

    base_domain = urlparse(start_url).netloc

    with httpx.Client(follow_redirects=True, timeout=15.0, verify=False) as client:
        while queue:
            current_url, current_depth = queue.pop(0)

            # Normalize URL by removing fragments
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
                response = client.get(normalized_url, headers={"User-Agent": "Mozilla/5.0"})
                if response.status_code != 200 or "text/html" not in response.headers.get(
                    "Content-Type", ""
                ):
                    continue

                soup = BeautifulSoup(response.content, "html.parser")
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    if isinstance(href, list):
                        href = href[0]
                    # Resolve relative URLs
                    full_url = urljoin(normalized_url, str(href))
                    parsed_full = urlparse(full_url)

                    # Ensure it's http/https and matches the base domain
                    if (
                        parsed_full.scheme in ["http", "https"]
                        and parsed_full.netloc == base_domain
                    ):
                        queue.append((full_url, current_depth + 1))

            except Exception as e:
                logger.warning(f"Failed to crawl {normalized_url}: {e}")

    logger.info(f"Crawling complete. Found {len(results)} URLs within depth {max_depth}.")
    return results
