"""Notion API integration: create a page from a converted Markdown file.

Uses ``core.http.get_client()`` rather than a raw ``httpx.Client`` (unlike
``obsidian_rest.py``, which has no documented reason for bypassing it and
appears to simply predate the centralized helper). ``get_client()`` already
covers everything needed here — custom headers (Authorization, Notion-Version),
JSON bodies, and GET/POST/PATCH — so there is no technical blocker to using it.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from convmd.core.http import get_client

logger = logging.getLogger(__name__)

NOTION_VERSION = "2022-06-28"
NOTION_API_BASE = "https://api.notion.com/v1"
_TIMEOUT = 10.0
_MAX_CHILDREN_PER_REQUEST = 100

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n+", re.DOTALL)
_STRING_FIELD_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):\s*"(.*)"\s*$')
_LIST_ITEM_RE = re.compile(r'^\s*-\s*"?(.*?)"?\s*$')


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse the minimal subset of ``generate_frontmatter`` output needed here.

    A purpose-built parser (rather than reusing ``exporters.json_exporter``)
    to avoid an integrations -> exporters import and because that parser's
    inline-array regex does not handle the block-style ``tags:\\n  - "x"``
    list that ``generate_frontmatter`` actually emits.
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text

    fm: dict[str, Any] = {}
    lines = m.group(1).split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        list_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*$", line)
        if list_match:
            key = list_match.group(1)
            items: list[str] = []
            i += 1
            while i < len(lines) and lines[i].startswith("  -"):
                item_m = _LIST_ITEM_RE.match(lines[i])
                if item_m:
                    items.append(item_m.group(1))
                i += 1
            fm[key] = items
            continue

        str_match = _STRING_FIELD_RE.match(line)
        if str_match:
            fm[str_match.group(1)] = str_match.group(2)
        else:
            plain_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
            if plain_match:
                val = plain_match.group(2).strip()
                fm[plain_match.group(1)] = [] if val == "[]" else val
        i += 1

    body = text[m.end() :]
    return fm, body


def _paragraphs_to_blocks(body: str) -> list[dict[str, Any]]:
    """Convert Markdown body text into simple Notion paragraph blocks.

    v1 keeps this deliberately simple: each blank-line-separated chunk becomes
    one paragraph block. Headings/lists/code blocks are not special-cased yet;
    this function is the single seam to extend later for richer block types.

    Known v1 limitation: Notion rejects any single rich_text content over
    2000 characters (400 error), which fails the whole export. A very long
    paragraph with no blank-line break (e.g. an unbroken transcript/OCR block)
    can hit this. Not handled here — left as a follow-up (slice long
    paragraphs) rather than expanding v1 scope.
    """
    blocks = []
    for para in body.split("\n\n"):
        stripped = para.strip()
        if not stripped:
            continue
        blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": stripped}}]},
            }
        )
    return blocks


def _find_title_property(schema: dict[str, Any]) -> str | None:
    """Find the name of the database property with type 'title'.

    Notion requires the page's title to be set on whichever property the
    database schema designates as type "title" (the property is not always
    named "Name" or "Title"), so the schema must be fetched first.
    """
    for name, definition in schema.get("properties", {}).items():
        if definition.get("type") == "title":
            return str(name)
    return None


def export_to_notion(file_path: Path, api_token: str, database_id: str) -> bool:
    """Export a Markdown file as a new page in a Notion database."""
    if not file_path.exists():
        return False

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

    try:
        text = file_path.read_text(encoding="utf-8")
        fm, body = _parse_frontmatter(text)
        title = fm.get("title") or file_path.stem
        source = fm.get("source")
        tags = fm.get("tags") or []

        with get_client(timeout=_TIMEOUT) as client:
            schema_response = client.get(
                f"{NOTION_API_BASE}/databases/{database_id}", headers=headers
            )
            schema_response.raise_for_status()
            schema = schema_response.json()

            title_prop = _find_title_property(schema)
            if not title_prop:
                logger.error(f"Notion database {database_id} has no title property.")
                return False

            properties: dict[str, Any] = {
                title_prop: {"title": [{"text": {"content": str(title)}}]}
            }

            db_properties = schema.get("properties", {})
            if source and "Source" in db_properties and db_properties["Source"].get("type") == "url":
                properties["Source"] = {"url": str(source)}
            if tags and "Tags" in db_properties and db_properties["Tags"].get("type") == "multi_select":
                properties["Tags"] = {"multi_select": [{"name": str(t)} for t in tags]}

            all_blocks = _paragraphs_to_blocks(body)
            first_batch, remaining = all_blocks[:_MAX_CHILDREN_PER_REQUEST], all_blocks[_MAX_CHILDREN_PER_REQUEST:]

            payload = {
                "parent": {"database_id": database_id},
                "properties": properties,
                "children": first_batch,
            }
            create_response = client.post(
                f"{NOTION_API_BASE}/pages", headers=headers, content=json.dumps(payload)
            )
            create_response.raise_for_status()
            page = create_response.json()
            page_id = page["id"]

            # Notion allows at most 100 children per call; append the rest via
            # follow-up PATCH calls in batches rather than truncating content.
            for start in range(0, len(remaining), _MAX_CHILDREN_PER_REQUEST):
                batch = remaining[start : start + _MAX_CHILDREN_PER_REQUEST]
                append_response = client.patch(
                    f"{NOTION_API_BASE}/blocks/{page_id}/children",
                    headers=headers,
                    content=json.dumps({"children": batch}),
                )
                append_response.raise_for_status()

        logger.info(f"Successfully exported {file_path.name} to Notion database {database_id}.")
        return True
    except Exception as e:
        logger.error(f"Failed to export to Notion: {e}")
        return False
