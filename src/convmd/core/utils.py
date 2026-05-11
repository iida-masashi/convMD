import re
from datetime import datetime, timezone
from typing import Sequence


def generate_frontmatter(title: str, url: str, tags: Sequence[str] | None = None) -> str:
    """Generates Obsidian-compatible frontmatter."""
    if tags is None:
        tags = []

    tags_str = ", ".join(tags)
    # Use timezone-aware datetime (UTC)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return f'---\ntitle: "{title}"\nsource: "{url}"\ndate: {date_str}\ntags: [{tags_str}]\n---\n\n'


def sanitize_filename(title: str) -> str:
    """Sanitizes a string to be used as a valid filename across OS."""
    # Remove invalid characters for Windows/Linux/Mac
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title).strip()[:100]
    return safe_title if safe_title else "Untitled"
