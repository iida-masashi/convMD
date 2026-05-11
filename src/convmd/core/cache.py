"""SQLite-backed fetch cache for ETag / Last-Modified + content-hash diffing."""

from __future__ import annotations

import difflib
import hashlib
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)

_DB_NAME = ".convmd.db"

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS fetches (
    url TEXT PRIMARY KEY,
    content_hash TEXT,
    etag TEXT,
    last_modified TEXT,
    fetched_at TEXT,
    output_path TEXT,
    body TEXT
);
"""


def _db_path(output_dir: Path) -> Path:
    return output_dir / _DB_NAME


@contextmanager
def _conn(output_dir: Path) -> Iterator[sqlite3.Connection]:
    output_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_db_path(output_dir))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_validators(output_dir: Path, url: str) -> tuple[str | None, str | None]:
    """Return ``(etag, last_modified)`` for a URL or (None, None) if unknown."""
    with _conn(output_dir) as c:
        row = c.execute(
            "SELECT etag, last_modified FROM fetches WHERE url = ?", (url,)
        ).fetchone()
    if not row:
        return None, None
    return row[0], row[1]


def get_previous(output_dir: Path, url: str) -> tuple[str | None, str | None]:
    """Return ``(content_hash, body)`` for the last successful fetch of URL."""
    with _conn(output_dir) as c:
        row = c.execute(
            "SELECT content_hash, body FROM fetches WHERE url = ?", (url,)
        ).fetchone()
    if not row:
        return None, None
    return row[0], row[1]


def record(
    output_dir: Path,
    url: str,
    *,
    body: str,
    output_path: Path | None,
    etag: str | None,
    last_modified: str | None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _conn(output_dir) as c:
        c.execute(
            "INSERT OR REPLACE INTO fetches "
            "(url, content_hash, etag, last_modified, fetched_at, output_path, body) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                url,
                hash_text(body),
                etag,
                last_modified,
                now,
                str(output_path) if output_path else None,
                body,
            ),
        )


def diff(previous_body: str, new_body: str, *, url: str) -> str | None:
    """Return a unified diff string, or None if the bodies are identical."""
    if previous_body == new_body:
        return None
    diff_lines = difflib.unified_diff(
        previous_body.splitlines(),
        new_body.splitlines(),
        fromfile=f"{url} (previous)",
        tofile=f"{url} (current)",
        lineterm="",
    )
    return "\n".join(diff_lines)
