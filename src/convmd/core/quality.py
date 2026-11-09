"""Post-conversion output checks and the optional origin-URL line.

``check_output`` only reports problems (the caller logs them as warnings); it never
changes or deletes the file. ``add_origin_line`` is opt-in (``--origin-line``) because
some publishers (e.g. Quartz) do not render the frontmatter ``source:`` field.
"""

from __future__ import annotations

import re
from pathlib import Path

MAX_OUTPUT_BYTES = 1_000_000
_MIN_BODY_CHARS = 20
_CJK_PROBE_CHARS = 2000
_ORIGIN_PREFIX = "> 原典URL:"
_FRONTMATTER_RE = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n", re.DOTALL)
_SOURCE_RE = re.compile(r'^source:\s*"?(https?://[^"\r\n]+)"?\s*$', re.MULTILINE)


def _split_frontmatter(text: str) -> tuple[str, str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return "", text
    return text[: m.end()], text[m.end() :]


def check_output(path: Path) -> list[str]:
    """Return human-readable problems found in a converted Markdown file (empty if none)."""
    from convmd.parsers.office import _is_garbled  # shared mojibake heuristic

    try:
        data = path.read_bytes()
        text = data.decode("utf-8", errors="replace")
    except OSError:
        return []
    problems: list[str] = []
    _, body = _split_frontmatter(text)
    if len(body.strip()) < _MIN_BODY_CHARS:
        problems.append("body is empty or nearly empty")
    if len(data) > MAX_OUTPUT_BYTES:
        problems.append(f"output is {len(data) / 1_000_000:.1f}MB (over {MAX_OUTPUT_BYTES // 1_000_000}MB)")
    if "�" in body[:_CJK_PROBE_CHARS] or _is_garbled(body):
        problems.append("text looks garbled (replacement characters or broken font mapping)")
    return problems


def add_origin_line(path: Path) -> bool:
    """Insert ``> 原典URL: <source>`` after the frontmatter. Returns True if the file changed.

    Does nothing when the file has no ``https`` ``source:`` in its frontmatter or already
    has the line. Preserves the file's existing line endings.
    """
    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    front, body = _split_frontmatter(text)
    m = _SOURCE_RE.search(front)
    if not m or _ORIGIN_PREFIX in body[:500]:
        return False
    nl = "\r\n" if "\r\n" in front else "\n"
    rest = body.lstrip("\r\n")
    new_text = f"{front}{nl}{_ORIGIN_PREFIX} {m.group(1)}{nl}{nl}{rest}"
    path.write_bytes(new_text.encode("utf-8"))
    return True
