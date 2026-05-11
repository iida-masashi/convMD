"""Podcast RSS fetcher — downloads each episode's MP3 and routes to the audio parser."""

from __future__ import annotations

import logging
import re
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

from convmd.constants import DOWNLOAD_TIMEOUT
from convmd.core.http import get_client, get_html
from convmd.core.utils import sanitize_filename

logger = logging.getLogger(__name__)


def _is_rss(text: str) -> bool:
    head = text.lstrip()[:200].lower()
    return "<rss" in head or "<feed" in head


def _episode_entries(rss_text: str, limit: int) -> list[tuple[str, str]]:
    """Return ``[(episode_title, mp3_url), ...]`` from an RSS feed."""
    try:
        root = ET.fromstring(rss_text)
    except ET.ParseError as e:
        logger.error(f"Failed to parse RSS: {e}")
        return []

    out: list[tuple[str, str]] = []
    for item in root.iter("item"):
        title_el = item.find("title")
        title = title_el.text.strip() if title_el is not None and title_el.text else "episode"
        enc = item.find("enclosure")
        if enc is not None:
            mp3 = enc.attrib.get("url")
            if mp3:
                out.append((title, mp3))
        if len(out) >= limit:
            break
    return out


def convert_podcast(url: str, output_dir: Path, *, limit: int = 1) -> Path | None:
    """Fetch up to ``limit`` recent podcast episodes and transcribe them."""
    text = get_html(url)
    if not text or not _is_rss(text):
        logger.warning(f"URL does not appear to be an RSS feed: {url}")
        return None

    entries = _episode_entries(text, limit)
    if not entries:
        logger.warning(f"No episodes found in RSS at {url}")
        return None

    from convmd.parsers.media.audio import convert_audio_file

    last_path: Path | None = None
    for ep_title, mp3_url in entries:
        safe = sanitize_filename(ep_title)
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / re.sub(r'[\\/*?:"<>|]', "", safe + ".mp3")
            try:
                with get_client(timeout=DOWNLOAD_TIMEOUT) as client:
                    response = client.get(mp3_url)
                    response.raise_for_status()
                    local.write_bytes(response.content)
            except Exception as e:
                logger.warning(f"Failed to download episode {ep_title}: {e}")
                continue
            result = convert_audio_file(local, output_dir)
            if result:
                last_path = result
    return last_path
