import logging
import os
from pathlib import Path
from typing import Optional

import httpx

from convmd.core.ocr import transcribe_image_with_gemini

logger = logging.getLogger(__name__)


def download_image(url: str, output_path: Path) -> None:
    """Download an image from a URL to the local filesystem."""
    with httpx.Client(follow_redirects=True, timeout=30.0, verify=False) as client:
        response = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        output_path.write_bytes(response.content)


def process_iiif_manifest(
    manifest_url: str, image_dir: Path, ocr_prompt: Optional[str] = None
) -> str:
    """
    IIIFマニフェストURLから画像をダウンロードし、MarkdownフォーマットのリンクとOCR結果を生成する。
    """
    images_markdown = ""
    try:
        res = httpx.get(manifest_url, timeout=10.0)
        res.raise_for_status()
        manifest_data = res.json()

        sequences = manifest_data.get("sequences", [])
        if sequences:
            image_dir.mkdir(parents=True, exist_ok=True)
            canvases = sequences[0].get("canvases", [])
            logger.info(f"Found {len(canvases)} images in IIIF manifest.")

            for i, canvas in enumerate(canvases):
                try:
                    images = canvas.get("images", [])
                    if not images:
                        continue

                    # IIIFのフル画像URLを取得
                    full_img_url = images[0]["resource"]["@id"]

                    img_filename = f"page_{i + 1:04d}.jpg"
                    img_path = image_dir / img_filename

                    # 画像のダウンロード実行
                    download_image(full_img_url, img_path)

                    # Markdownへの埋め込みリンク (Obsidian対応の相対パス)
                    images_markdown += f"![[images/{img_filename}]]\n"

                    # 環境変数が設定されていればOCRを実行
                    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
                        transcription = transcribe_image_with_gemini(img_path, prompt=ocr_prompt)
                        if transcription:
                            images_markdown += "\n> " + transcription.replace("\n", "\n> ") + "\n\n"

                except Exception as e:
                    logger.warning(f"Failed to process image {i + 1}: {e}")

    except Exception as e:
        logger.warning(f"Failed to process IIIF manifest from {manifest_url}: {e}")

    return images_markdown
