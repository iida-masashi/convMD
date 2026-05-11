import logging
import re
from pathlib import Path
from typing import Any

import httpx
from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore

from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)

def get_video_id(url: str) -> str | None:
    """Extracts YouTube video ID from URL."""
    match = re.search(r'(?:v=|/)([0-9A-Za-z_-]{11}).*', url)
    if match:
        return match.group(1)
    return None

def get_video_title(video_id: str) -> str:
    """Fetches the video title using YouTube oEmbed API."""
    url = f"https://www.youtube.com/oembed?url=http://www.youtube.com/watch?v={video_id}&format=json"
    try:
        with httpx.Client(follow_redirects=True, timeout=5.0) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
            return str(data.get('title', f"YouTube_Video_{video_id}"))
    except Exception as e:
        logger.warning(f"Failed to fetch video title for {video_id}: {e}")
        return f"YouTube_Video_{video_id}"

def format_time(seconds: float) -> str:
    """Formats seconds into HH:MM:SS or MM:SS."""
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

def convert_youtube(url: str, output_dir: Path) -> Path | None:
    """
    Fetches transcript for a YouTube video and converts it into a Markdown file.
    """
    video_id = get_video_id(url)
    if not video_id:
        logger.error(f"Could not extract YouTube Video ID from {url}")
        return None

    logger.info(f"Fetching transcript for video ID: {video_id}...")

    try:
        # 1. Fetch the transcript list
        api: Any = YouTubeTranscriptApi
        transcript_list = api.list_transcripts(video_id)  # type: ignore
        # 2. Try to find Japanese or English manual transcripts first
        try:
            transcript_obj = transcript_list.find_transcript(['ja', 'en'])
            transcript = transcript_obj.fetch()
        except Exception:
            # Fallback to the first available transcript
            for t in transcript_list:
                transcript = t.fetch()
                break
    except Exception as e:
        # Final fallback using the simple method
        try:
            api2: Any = YouTubeTranscriptApi
            transcript = api2.get_transcript(video_id, languages=['ja', 'en'])
        except Exception as e2:
            logger.error(f"Failed to fetch YouTube transcript: {e} / {e2}")
            return None

    title = get_video_title(video_id)

    # Obsidian Frontmatter
    frontmatter = generate_frontmatter(title, url, tags=["youtube", "transcript"])

    # Body with Thumbnail
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

    lines = [
        frontmatter,
        f"![Thumbnail]({thumbnail_url})\n\n",
        "## 動画情報\n",
        f"- **タイトル**: {title}\n",
        f"- **URL**: {url}\n\n",
        "## 文字起こし\n\n"
    ]

    for entry in transcript:
        # Type fallback depending on transcript_api version
        start = float(entry.get('start', 0.0))
        text = str(entry.get('text', ''))

        start_time = format_time(start)
        text = text.replace('\n', ' ')
        lines.append(f"**[{start_time}]** {text}\n\n")

    safe_title = sanitize_filename(title)
    filename = f"{safe_title}.md"
    path = output_dir / filename

    path.write_text("".join(lines), encoding="utf-8")

    logger.info(f"Saved YouTube transcript to {path}")
    return path
