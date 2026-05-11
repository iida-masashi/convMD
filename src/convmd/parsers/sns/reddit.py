"""Reddit thread fetcher via the public .json endpoint."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from convmd.core.http import get_json
from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)


_THREAD_RE = re.compile(
    r"https?://(?:www\.|old\.)?reddit\.com/r/([^/]+)/comments/([a-zA-Z0-9]+)"
)


def convert_reddit(url: str, output_dir: Path, *, comment_limit: int = 20) -> Path | None:
    m = _THREAD_RE.search(url)
    if not m:
        logger.warning(f"Unrecognized Reddit URL: {url}")
        return None
    sub, thread_id = m.group(1), m.group(2)
    json_url = f"https://www.reddit.com/r/{sub}/comments/{thread_id}.json?limit={comment_limit}"
    data = get_json(json_url)
    if not data or not isinstance(data, list) or len(data) < 2:
        return None

    post = data[0]["data"]["children"][0]["data"]
    title = post.get("title", "Reddit Thread")
    body = post.get("selftext", "")
    permalink = "https://www.reddit.com" + post.get("permalink", "")

    lines: list[str] = [
        generate_frontmatter(title, permalink, tags=["reddit", sub]),
        f"# {title}\n\n",
        f"**r/{sub}** — posted by u/{post.get('author', '?')}\n\n",
    ]
    if body:
        lines.append(body + "\n\n")
    lines.append("## Comments\n\n")

    comments = data[1]["data"]["children"]
    for c in comments[:comment_limit]:
        cd = c.get("data", {})
        if c.get("kind") != "t1":
            continue
        author = cd.get("author", "?")
        text = cd.get("body", "")
        score = cd.get("score", 0)
        lines.append(f"**u/{author}** ({score} pts):\n\n{text}\n\n---\n\n")

    safe = sanitize_filename(title)
    path = output_dir / f"{safe}.md"
    path.write_text("".join(lines), encoding="utf-8")
    logger.info(f"Saved Reddit thread to {path}")
    return path
