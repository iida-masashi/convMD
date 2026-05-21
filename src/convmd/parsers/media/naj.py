"""National Archives of Japan (国立公文書館) IIIF extraction."""

from __future__ import annotations

import logging
from pathlib import Path

from convmd.core.iiif import process_iiif_manifest
from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)

def convert_naj(url: str, output_dir: Path, *, ocr: bool = False) -> None:
    parts = [p for p in url.strip("/").split("/") if p]
    item_id = None
    if "img" in parts:
        try:
            idx = parts.index("img")
            item_id = parts[idx + 1].split("#")[0]
        except (ValueError, IndexError):
            pass
    elif "iiif" in parts:
         try:
            idx = parts.index("iiif")
            item_id = parts[idx + 1]
         except:
            pass

    if not item_id:
        logger.error(f"Could not extract item ID from: {url}")
        return

    logger.info(f"Processing NAJ Item ID: {item_id}")
    manifest_api = f"https://www.digital.archives.go.jp/api/iiif/{item_id}/manifest.json"

    title = f"NAJ_{item_id}"
    logger.info(f"Fetching IIIF images for {title} (OCR enabled: {ocr})...")
    image_dir = output_dir / "images"
    ocr_prompt = None
    if ocr:
        ocr_prompt = (
            "これは日本の古典籍（和古書や漢籍）の画像です。"
            "画像に書かれているテキストを正確に文字起こし（翻刻）してください。"
            "【重要な指示】\n"
            "1. 挨拶や「翻刻しました」等の会話文は一切出力しないでください。\n"
            "2. 「【右頁】」や「（右から左へ）」のようなレイアウトの解説、または「（虫損）」のような状態の注記は絶対に書かないでください。\n"
            "3. 元の書籍に書かれている漢字（および元の割注）だけを、純粋な平文として出力してください。"
        )

    images_markdown = process_iiif_manifest(
        manifest_url=manifest_api,
        image_dir=image_dir,
        ocr_prompt=ocr_prompt,
    )
    if not images_markdown:
        logger.warning(f"Failed to process IIIF images for {url}")
        return

    frontmatter = generate_frontmatter(
        title=title,
        url=url,
        tags=["naj", "iiif", "web_clip"],
    )

    markdown = f"{frontmatter}\n\n# {title}\n\n{images_markdown}"

    safe_title = sanitize_filename(title)
    output_path = output_dir / f"{safe_title}.md"
    output_path.write_text(markdown, encoding="utf-8")
    logger.info(f"Saved to {output_path}")
    return output_path

