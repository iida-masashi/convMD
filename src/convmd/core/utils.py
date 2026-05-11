"""Frontmatter generation and filename sanitization helpers."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Mapping, Sequence


def _yaml_quote(value: str) -> str:
    """Emit a YAML double-quoted scalar that survives embedded quotes/backslashes."""
    return json.dumps(value, ensure_ascii=False)


def generate_frontmatter(
    title: str,
    url: str,
    tags: Sequence[str] | None = None,
    *,
    extra: Mapping[str, str] | None = None,
    author: str | None = None,
    published_at: str | None = None,
    reading_time_min: int | None = None,
    excerpt: str | None = None,
    cover: str | None = None,
) -> str:
    """Generate Obsidian-compatible YAML frontmatter.

    Backwards-compatible signature: title/url/tags positional usage is preserved.
    Optional keyword-only metadata (author, published_at, reading_time_min, excerpt, cover,
    plus arbitrary ``extra`` dict) is appended when provided.
    """
    if tags is None:
        tags = []
    tags_str = ", ".join(tags)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "---",
        f"title: {_yaml_quote(title)}",
        f"source: {_yaml_quote(url)}",
        f"date: {date_str}",
        f"tags: [{tags_str}]",
    ]
    if author:
        lines.append(f"author: {_yaml_quote(author)}")
    if published_at:
        lines.append(f"published_at: {_yaml_quote(published_at)}")
    if reading_time_min is not None:
        lines.append(f"reading_time_min: {reading_time_min}")
    if excerpt:
        lines.append(f"excerpt: {_yaml_quote(excerpt)}")
    if cover:
        lines.append(f"cover: {_yaml_quote(cover)}")
    if extra:
        for key, val in extra.items():
            lines.append(f"{key}: {_yaml_quote(str(val))}")
    lines.append("---\n\n")
    return "\n".join(lines)


def sanitize_filename(title: str) -> str:
    """Sanitize a string for use as a filename across Windows/Linux/macOS."""
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title).strip()[:100]
    return safe_title if safe_title else "Untitled"


def estimate_reading_time(text: str, *, cjk_chars_per_min: int = 1000, latin_words_per_min: int = 250) -> int:
    """Rough reading-time estimator. CJK chars and non-CJK words are weighted separately."""
    cjk = sum(1 for c in text if "぀" <= c <= "ヿ" or "一" <= c <= "鿿")
    rest = re.findall(r"[A-Za-z0-9]+", text)
    minutes = cjk / cjk_chars_per_min + len(rest) / latin_words_per_min
    return max(1, int(round(minutes)))
