"""Twitter/X timeline extractor via the public syndication endpoint."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from convmd.constants import DEFAULT_TIMEOUT
from convmd.core.http import get_client
from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)


def fetch_twitter_timeline(screen_name: str) -> list[dict[str, Any]] | None:
    """Fetch a user's recent tweets via the syndication endpoint."""
    url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{screen_name}"
    headers = {
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
    }

    logger.info(f"Fetching timeline for @{screen_name}...")
    try:
        with get_client(timeout=DEFAULT_TIMEOUT) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            html = response.text
    except Exception as e:
        logger.error(f"Failed to fetch timeline for @{screen_name}: {e}")
        return None

    match = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        logger.error("Could not find timeline data in the response.")
        return None

    try:
        data = json.loads(match.group(1))
        entries = data["props"]["pageProps"]["timeline"]["entries"]
        return list(entries)
    except Exception as e:
        logger.error(f"Error parsing JSON data: {e}")
        return None


def convert_twitter(screen_name: str, output_dir: Path) -> Path | None:
    entries = fetch_twitter_timeline(screen_name)
    if not entries:
        return None

    tweets: list[dict[str, Any]] = []
    for entry in entries:
        if entry.get("type") != "tweet":
            continue
        tweet_data = entry.get("content", {}).get("tweet", {})
        tweet_id = tweet_data.get("id_str")
        created_at = tweet_data.get("created_at")
        text = tweet_data.get("text", "")

        media_urls: list[str] = []
        entities = tweet_data.get("entities", {})
        if "media" in entities:
            for m in entities["media"]:
                media_url = m.get("media_url_https")
                if media_url:
                    media_urls.append(media_url)
                    url_tco = m.get("url", "")
                    if url_tco:
                        text = text.replace(url_tco, "").strip()

        tweets.append({"id": tweet_id, "date": created_at, "text": text, "media": media_urls})

    if not tweets:
        logger.info(f"No tweets found for @{screen_name}.")
        return None

    logger.info(f"Found {len(tweets)} tweets. Converting to Markdown...")
    safe_name = sanitize_filename(screen_name)
    md_path = output_dir / f"{safe_name}_tweets.md"

    frontmatter = generate_frontmatter(
        title=f"@{screen_name} の投稿まとめ",
        url=f"https://x.com/{screen_name}",
        tags=["sns", "twitter", screen_name],
    )

    lines = [frontmatter, f"# @{screen_name} の投稿まとめ\n\n", "---\n\n"]
    for t in tweets:
        lines.append(f"### {t['date']} (ID: {t['id']})\n\n")
        lines.append(f"{t['text']}\n\n")
        for m in t["media"]:
            lines.append(f"![image]({m})\n\n")
        lines.append(f"[Twitterで見る](https://x.com/{screen_name}/status/{t['id']})\n\n")
        lines.append("---\n\n")

    md_path.write_text("".join(lines), encoding="utf-8")
    logger.info(f"Saved {len(tweets)} tweets to {md_path}")
    return md_path
