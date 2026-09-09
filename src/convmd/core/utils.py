"""Frontmatter generation and filename sanitization helpers."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


def _yaml_format(value: Any, indent: int = 0) -> str:
    """Helper to format values as basic YAML without external libraries."""
    padding = " " * indent
    if isinstance(value, (list, tuple)):
        if not value:
            return "[]"
        items = [f"\n{padding}  - {_yaml_format(v).strip()}" for v in value]
        return "".join(items)
    elif isinstance(value, str):
        # Fall back to json.dumps for safe quote escaping
        return json.dumps(value, ensure_ascii=False)
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif value is None:
        return "null"
    else:
        return str(value)

def generate_frontmatter(
    title: str,
    url: str,
    tags: Sequence[str] | None = None,
    *,
    extra: Mapping[str, Any] | None = None,
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
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        "---",
        f"title: {_yaml_format(title)}",
        f"source: {_yaml_format(url)}",
        f"created_at: {_yaml_format(date_str)}",
    ]

    if tags:
        lines.append(f"tags:{_yaml_format(tags)}")
    else:
        lines.append("tags: []")

    if author:
        lines.append(f"author: {_yaml_format(author)}")
    if published_at:
        lines.append(f"published_at: {_yaml_format(published_at)}")
    if reading_time_min is not None:
        lines.append(f"reading_time_min: {reading_time_min}")
    if excerpt:
        lines.append(f"excerpt: {_yaml_format(excerpt)}")
    if cover:
        lines.append(f"cover: {_yaml_format(cover)}")

    if extra:
        for key, val in extra.items():
            if key == "aliases" and isinstance(val, (list, tuple)):
                lines.append(f"aliases:{_yaml_format(val)}")
            else:
                lines.append(f"{key}: {_yaml_format(val)}")

    lines.append("---\n\n")
    return "\n".join(lines)


def sanitize_filename(title: str, max_bytes: int = 200) -> str:
    """Sanitize a string for use as a filename across Windows/Linux/macOS.

    Ensures the sanitized name does not exceed `max_bytes` in UTF-8 encoding
    to prevent filesystem errors on Linux (ext4 255-byte limit) while stripping
    invalid characters for Windows.
    """
    safe_title = re.sub(r'[\x00-\x1f\\/*?:"<>|]', "", title).strip(" .")
    if not safe_title:
        return "Untitled"

    encoded = safe_title.encode("utf-8")
    if len(encoded) > max_bytes:
        safe_title = encoded[:max_bytes].decode("utf-8", errors="ignore").rstrip(" .")

    return safe_title if safe_title else "Untitled"


def estimate_reading_time(text: str, *, cjk_chars_per_min: int = 1000, latin_words_per_min: int = 250) -> int:
    """Rough reading-time estimator. CJK chars and non-CJK words are weighted separately."""
    cjk = sum(1 for c in text if "぀" <= c <= "ヿ" or "一" <= c <= "鿿")
    rest = re.findall(r"[A-Za-z0-9]+", text)
    minutes = cjk / cjk_chars_per_min + len(rest) / latin_words_per_min
    return max(1, int(round(minutes)))


def format_seconds_as_timestamp(seconds: float) -> str:
    """Format seconds as ``MM:SS`` or ``H:MM:SS`` for transcript/subtitle timestamps."""
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"
