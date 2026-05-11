import json
import logging
import re
from pathlib import Path
from typing import Any

import httpx

from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)


def fetch_twitter_timeline(screen_name: str) -> list[dict[str, Any]] | None:
    """Fetches a user's timeline from the syndication API using httpx."""
    url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{screen_name}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    }

    logger.info(f"Fetching timeline for @{screen_name}...")
    try:
        with httpx.Client(follow_redirects=True, timeout=10.0, verify=False) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            html = response.text
    except httpx.RequestError as e:
        logger.error(f"Failed to fetch timeline for @{screen_name}: {e}")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error {e.response.status_code} fetching timeline for @{screen_name}")
        return None

    # Extract __NEXT_DATA__ JSON from HTML
    match = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        logger.error("Could not find timeline data in the response.")
        return None

    json_data = match.group(1)
    try:
        data = json.loads(json_data)
        entries = data["props"]["pageProps"]["timeline"]["entries"]
        return list(entries)  # type: ignore
    except Exception as e:
        logger.error(f"Error parsing JSON data: {e}")
        return None


def convert_twitter(screen_name: str, output_dir: Path) -> Path | None:
    """Fetches and converts recent tweets to a single Markdown file."""
    entries = fetch_twitter_timeline(screen_name)
    if not entries:
        return None

    tweets = []

    for entry in entries:
        if entry.get("type") == "tweet":
            tweet_data = entry.get("content", {}).get("tweet", {})

            tweet_id = tweet_data.get("id_str")
            created_at = tweet_data.get("created_at")  # e.g., "Sat Sep 14 01:16:40 +0000 2024"
            text = tweet_data.get("text", "")

            # Since datetime format from Twitter is rigid, we'll keep it as a string for simplicity or parse it
            date_str = created_at

            # Extract Media
            media_urls = []
            entities = tweet_data.get("entities", {})
            if "media" in entities:
                for m in entities["media"]:
                    media_url = m.get("media_url_https")
                    if media_url:
                        media_urls.append(media_url)
                        # Remove the t.co URL from text to keep it clean
                        url_tco = m.get("url", "")
                        if url_tco:
                            text = text.replace(url_tco, "").strip()

            tweets.append({"id": tweet_id, "date": date_str, "text": text, "media": media_urls})

    if not tweets:
        logger.info(f"No tweets found for @{screen_name}.")
        return None

    logger.info(f"Found {len(tweets)} tweets. Converting to Markdown...")

    safe_name = sanitize_filename(screen_name)
    md_filename = f"{safe_name}_tweets.md"
    md_path = output_dir / md_filename

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
