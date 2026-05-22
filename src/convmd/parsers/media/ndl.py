"""National Diet Library (国立国会図書館) Digital Collection IIIF extraction."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import httpx

from convmd.constants import DEFAULT_TIMEOUT
from convmd.core.iiif import process_iiif_manifest
from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)

_OCR_PROMPT = (
    "これは日本の古典籍や近代書籍の画像です。"
    "画像に書かれているテキストを正確に文字起こし（翻刻）してください。"
    "【重要な指示】\n"
    "1. 挨拶や「翻刻しました」等の会話文は一切出力しないでください。\n"
    "2. レイアウトの解説や状態の注記は絶対に書かないでください。\n"
    "3. 純粋な平文として出力してください。"
)

def convert_ndl(url: str, output_dir: Path, *, ocr: bool = False, **kwargs: Any) -> None:
    """Fetch NDL Digital Collection entry and IIIF images."""
    # Extract PID from url (e.g. https://dl.ndl.go.jp/pid/1234567 or info:ndljp/pid/1234567)
    match = re.search(r'pid/(\d+)', url)
    if not match:
        logger.error(f"Could not extract PID from NDL URL: {url}")
        return

    pid = match.group(1)
    logger.info(f"Processing NDL PID: {pid}")

    manifest_api = f"https://dl.ndl.go.jp/api/iiif/{pid}/manifest.json"

    try:
        res = httpx.get(manifest_api, timeout=DEFAULT_TIMEOUT)
        if res.status_code == 404:
            logger.error(f"IIIF Manifest not found for PID {pid}. This item might not be public or does not support IIIF.")
            return
        res.raise_for_status()
        manifest_data = res.json()
    except Exception as e:
        logger.error(f"Failed to fetch NDL manifest: {e}")
        return

    # Extract title from manifest
    title = manifest_data.get("label", f"NDL_{pid}")
    if isinstance(title, list):
        # Some manifests have label as list
        title = " ".join(title)

    # Sometimes it's a dict depending on IIIF version, handling strings simply
    if isinstance(title, dict):
        title = title.get("ja", [title.get("none", [f"NDL_{pid}"])[0]])[0]

    safe_title = sanitize_filename(str(title))

    # Extract author and other metadata if available
    metadata_list = manifest_data.get("metadata", [])
    author = "不明"
    published = "不明"
    for item in metadata_list:
        label = item.get("label", "")
        value = item.get("value", "")
        if "著者" in label or "Creator" in label:
            author = value
        elif "出版年月日" in label or "Date" in label:
            published = value

    # IIIF processing
    image_dir = output_dir / safe_title / "images"

    logger.info(f"Fetching IIIF images for {title} (OCR enabled: {ocr})...")
    images_markdown = process_iiif_manifest(
        manifest_api,
        image_dir,
        ocr_prompt=_OCR_PROMPT if ocr else None,
        secondary_prompt=None, # Add bilingual translation if needed
    )

    frontmatter = generate_frontmatter(
        str(title),
        url,
        tags=["ndl", "iiif", "web_clip"],
        author=str(author),
        extra={"pid": pid},
    )

    body = [
        f"# {title}\n\n",
        "## 書誌情報\n",
        f"- **著者**: {author}\n",
        f"- **出版年月日**: {published}\n",
        f"- **URL**: {url}\n\n",
    ]

    if images_markdown:
        body.append("## 画像および翻刻\n")
        body.append(images_markdown)

    md_content = frontmatter + "".join(body)

    output_dir.mkdir(parents=True, exist_ok=True)
    if image_dir.exists():
        md_path = output_dir / safe_title / f"{safe_title}.md"
    else:
        md_path = output_dir / f"{safe_title}.md"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    logger.info(f"Saved to {md_path}")
