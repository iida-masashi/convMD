"""YouTube transcript fetcher with chapter detection and thumbnail integration."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore

from convmd.core.download import process_images
from convmd.core.http import get_client, get_html
from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)


def get_video_id(url: str) -> str | None:
    match = re.search(r"(?:v=|/)([0-9A-Za-z_-]{11}).*", url)
    if match:
        return match.group(1)
    return None


def get_video_title(video_id: str) -> str:
    url = (
        f"https://www.youtube.com/oembed?url=http://www.youtube.com/watch?v={video_id}&format=json"
    )
    try:
        with get_client(timeout=5.0) as client:
            response = client.get(url)
            response.raise_for_status()
            return str(response.json().get("title", f"YouTube_Video_{video_id}"))
    except Exception as e:
        logger.warning(f"Failed to fetch video title for {video_id}: {e}")
        return f"YouTube_Video_{video_id}"


def format_time(seconds: float) -> str:
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


_CHAPTER_RE = re.compile(
    r'"chapterRenderer"\s*:\s*\{[^{}]*?"title"\s*:\s*\{\s*"simpleText"\s*:\s*"([^"]+)"\s*\}[^{}]*?"timeRangeStartMillis"\s*:\s*(\d+)',
    re.DOTALL,
)

_DESC_CHAPTER_RE = re.compile(
    r"(?m)^\s*((?:\d+:)?\d{1,2}:\d{2})\s+(.+)$"
)


def _parse_timestamp(ts: str) -> float:
    parts = ts.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0.0


def fetch_chapters(video_id: str) -> list[tuple[float, str]]:
    """Return ``[(start_seconds, title), ...]`` or empty list if none found."""
    html = get_html(f"https://www.youtube.com/watch?v={video_id}")
    if not html:
        return []

    chapters: list[tuple[float, str]] = []
    for title, start_ms in _CHAPTER_RE.findall(html):
        try:
            chapters.append((int(start_ms) / 1000.0, title))
        except ValueError:
            continue

    if chapters:
        chapters.sort(key=lambda x: x[0])
        return chapters

    desc_match = re.search(r'"shortDescription"\s*:\s*"((?:\\.|[^"\\])*)"', html)
    if desc_match:
        description = (
            desc_match.group(1)
            .encode("utf-8")
            .decode("unicode_escape", errors="ignore")
            .replace("\\n", "\n")
        )
        for ts, title in _DESC_CHAPTER_RE.findall(description):
            chapters.append((_parse_timestamp(ts), title.strip()))
        chapters.sort(key=lambda x: x[0])
    return chapters


def _fetch_transcript(video_id: str) -> list[dict[str, Any]] | None:
    try:
        api: Any = YouTubeTranscriptApi
        transcript_list = api.list_transcripts(video_id)
        try:
            return list(transcript_list.find_transcript(["ja", "en"]).fetch())
        except Exception:
            for t in transcript_list:
                return list(t.fetch())
    except Exception as e:
        try:
            api2: Any = YouTubeTranscriptApi
            return list(api2.get_transcript(video_id, languages=["ja", "en"]))
        except Exception as e2:
            logger.error(f"Failed to fetch YouTube transcript: {e} / {e2}")
            return None
    return None


def convert_youtube(url: str, output_dir: Path) -> Path | None:
    """Fetch transcript (+ chapters + thumbnail) for a YouTube video."""
    video_id = get_video_id(url)
    if not video_id:
        logger.error(f"Could not extract YouTube Video ID from {url}")
        return None

    logger.info(f"Fetching transcript for video ID: {video_id}...")
    transcript = _fetch_transcript(video_id)
    if transcript is None:
        return None

    title = get_video_title(video_id)
    chapters = fetch_chapters(video_id)
    if chapters:
        logger.info(f"Detected {len(chapters)} chapters.")

    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    cover_md = f"![Thumbnail]({thumbnail_url})\n\n"
    cover_md = process_images(cover_md, "https://img.youtube.com", output_dir)

    frontmatter = generate_frontmatter(title, url, tags=["youtube", "transcript"])

    lines: list[str] = [
        frontmatter,
        cover_md,
        "## 動画情報\n",
        f"- **タイトル**: {title}\n",
        f"- **URL**: {url}\n\n",
        "## 文字起こし\n\n",
    ]

    def _entry_start(entry: Any) -> float:
        if isinstance(entry, dict):
            return float(entry.get("start", 0.0))
        return float(getattr(entry, "start", 0.0))

    def _entry_text(entry: Any) -> str:
        if isinstance(entry, dict):
            return str(entry.get("text", ""))
        return str(getattr(entry, "text", ""))

    if chapters:
        ch_idx = 0
        for entry in transcript:
            start = _entry_start(entry)
            while ch_idx < len(chapters) and chapters[ch_idx][0] <= start:
                ch_start, ch_title = chapters[ch_idx]
                lines.append(f"\n## [{format_time(ch_start)}] {ch_title}\n\n")
                ch_idx += 1
            text = _entry_text(entry).replace("\n", " ")
            lines.append(f"**[{format_time(start)}]** {text}\n\n")
    else:
        for entry in transcript:
            start = _entry_start(entry)
            text = _entry_text(entry).replace("\n", " ")
            lines.append(f"**[{format_time(start)}]** {text}\n\n")

    safe_title = sanitize_filename(title)
    path = output_dir / f"{safe_title}.md"
    path.write_text("".join(lines), encoding="utf-8")
    logger.info(f"Saved YouTube transcript to {path}")
    return path
