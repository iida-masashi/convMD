"""note.com creator profile fetcher."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from markdownify import markdownify as md

from convmd.core.http import get_json
from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)


def convert_note_com(urlname: str, output_dir: Path) -> Path | None:
    """Fetch all notes from a note.com creator and write them as Markdown files."""
    user_dir = output_dir / f"note_{sanitize_filename(urlname)}"
    user_dir.mkdir(parents=True, exist_ok=True)

    page = 1
    all_notes: list[dict] = []

    logger.info(f"Fetching note list for {urlname}...")
    while True:
        url = f"https://note.com/api/v2/creators/{urlname}/contents?kind=note&page={page}"
        data = get_json(url)
        if not data or "data" not in data or "contents" not in data["data"]:
            logger.warning("Failed to fetch notes or reached the end.")
            break

        notes = data["data"]["contents"]
        if not notes:
            break
        all_notes.extend(notes)
        if data["data"].get("isLastPage"):
            break
        page += 1

    if not all_notes:
        logger.warning(f"No notes found for creator {urlname}.")
        return None

    logger.info(f"Found {len(all_notes)} notes. Starting conversion...")
    for note in all_notes:
        key = note.get("key")
        title = note.get("name", "Untitled")
        publish_at = note.get("publishAt", "")
        if not key:
            continue

        try:
            note_data = get_json(f"https://note.com/api/v3/notes/{key}")
            if not note_data:
                continue

            html_body = note_data["data"]["body"]
            md_body = md(html_body, heading_style="ATX")

            date_prefix = ""
            if publish_at:
                match = re.match(r"^(\d{4}-\d{2}-\d{2})", publish_at)
                if match:
                    date_prefix = f"{match.group(1)}-"

            frontmatter = generate_frontmatter(
                title=title, url=f"https://note.com/{urlname}/n/{key}", tags=["sns", "note"]
            )

            filename = f"{date_prefix}{sanitize_filename(title)}.md"
            file_path = user_dir / filename
            file_path.write_text(frontmatter + md_body, encoding="utf-8")
            logger.info(f"Converted note: {filename}")

        except Exception as e:
            logger.error(f"Error converting note {key} ({title}): {e}")

    logger.info(f"Saved note articles to {user_dir}")
    return user_dir
