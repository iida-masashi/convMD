"""Scan an Obsidian vault for existing tags and normalize generated tags against them.

Three-tier matching:
  1. Exact case-insensitive match → canonical capitalization wins
  2. difflib close match ≥ cutoff → existing tag wins
  3. Otherwise → keep the new tag verbatim

CJK tags (containing Hiragana / Katakana / CJK Unified) skip step 2: fuzzy matching
behaves unreliably on 2-3 character Japanese strings.
"""

from __future__ import annotations

import difflib
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---", re.DOTALL)
_TAG_INLINE_LIST_RE = re.compile(r"^tags\s*:\s*\[(.*?)\]\s*$", re.MULTILINE)
_TAG_BLOCK_RE = re.compile(
    r"^tags\s*:\s*$\n((?:^[ \t]*-\s*.+\n?)+)",
    re.MULTILINE,
)
_TAG_ITEM_RE = re.compile(r"^[ \t]*-\s*(.+?)\s*$", re.MULTILINE)


def _is_cjk(tag: str) -> bool:
    return any(
        "぀" <= c <= "ヿ"  # Hiragana, Katakana
        or "一" <= c <= "鿿"  # CJK Unified
        for c in tag
    )


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s


def _extract_tags_from_frontmatter(text: str) -> list[str]:
    """Return tag strings from a markdown file's YAML frontmatter."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return []
    body = m.group(1)

    tags: list[str] = []

    inline = _TAG_INLINE_LIST_RE.search(body)
    if inline:
        for part in inline.group(1).split(","):
            t = _strip_quotes(part)
            if t:
                tags.append(t)

    block = _TAG_BLOCK_RE.search(body)
    if block:
        for item_match in _TAG_ITEM_RE.finditer(block.group(1)):
            t = _strip_quotes(item_match.group(1))
            if t:
                tags.append(t)

    return tags


def scan_vault_tags(vault_path: Path) -> set[str]:
    """Walk an Obsidian vault and return the set of all tags found in frontmatter."""
    if not vault_path.is_dir():
        logger.warning(f"Vault path is not a directory: {vault_path}")
        return set()

    tags: set[str] = set()
    for md_file in vault_path.rglob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        tags.update(_extract_tags_from_frontmatter(text))
    logger.info(f"Scanned vault {vault_path}: found {len(tags)} unique tags.")
    return tags


def normalize_tag(tag: str, existing: set[str], *, cutoff: float = 0.85) -> str:
    """Return the canonical existing tag if a match is found, otherwise the input verbatim."""
    if not tag or not existing:
        return tag

    lower_map = {e.lower(): e for e in existing}
    exact = lower_map.get(tag.lower())
    if exact is not None:
        return exact

    if _is_cjk(tag):
        return tag

    candidates = difflib.get_close_matches(tag, list(existing), n=1, cutoff=cutoff)
    if candidates:
        return candidates[0]

    return tag


def normalize_tags(
    tags: list[str], existing: set[str], *, cutoff: float = 0.85
) -> list[str]:
    """Map a list of generated tags through ``normalize_tag``, preserving order, deduplicating."""
    seen: set[str] = set()
    result: list[str] = []
    for t in tags:
        canon = normalize_tag(t, existing, cutoff=cutoff)
        if canon not in seen:
            seen.add(canon)
            result.append(canon)
    return result
