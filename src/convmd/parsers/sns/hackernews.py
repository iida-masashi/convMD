"""Hacker News item fetcher via Firebase API."""

from __future__ import annotations

import html
import logging
import re
from pathlib import Path

from convmd.core.http import get_json
from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)

_API = "https://hacker-news.firebaseio.com/v0/item/{}.json"


def _fetch_item(item_id: int) -> dict | None:
    return get_json(_API.format(item_id))


def _strip_html(text: str) -> str:
    text = re.sub(r"<p[^>]*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def _render_comment(c: dict, depth: int, comment_limit: int) -> str:
    if c.get("deleted") or c.get("dead"):
        return ""
    indent = "  " * depth
    author = c.get("by", "?")
    text = _strip_html(c.get("text", ""))
    out = f"{indent}- **{author}**: {text}\n"
    if depth < 1:
        for kid_id in (c.get("kids") or [])[:comment_limit]:
            kid = _fetch_item(kid_id)
            if kid:
                out += _render_comment(kid, depth + 1, comment_limit)
    return out


def convert_hackernews(url: str, output_dir: Path, *, comment_limit: int = 15) -> Path | None:
    m = re.search(r"[?&]id=(\d+)", url)
    if not m:
        logger.warning(f"Could not extract HN item id from {url}")
        return None
    item_id = int(m.group(1))
    item = _fetch_item(item_id)
    if not item:
        return None

    title = item.get("title", f"HN Item {item_id}")
    perma = f"https://news.ycombinator.com/item?id={item_id}"
    lines = [
        generate_frontmatter(title, perma, tags=["hackernews"]),
        f"# {title}\n\n",
        f"by **{item.get('by', '?')}** — {item.get('score', 0)} pts\n\n",
    ]
    if item.get("url"):
        lines.append(f"Link: {item['url']}\n\n")
    if item.get("text"):
        lines.append(_strip_html(item["text"]) + "\n\n")

    lines.append("## Comments\n\n")
    for kid_id in (item.get("kids") or [])[:comment_limit]:
        kid = _fetch_item(kid_id)
        if kid:
            lines.append(_render_comment(kid, 0, comment_limit))

    safe = sanitize_filename(title)
    path = output_dir / f"{safe}.md"
    path.write_text("".join(lines), encoding="utf-8")
    logger.info(f"Saved Hacker News thread to {path}")
    return path
