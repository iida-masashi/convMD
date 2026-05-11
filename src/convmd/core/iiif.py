"""IIIF manifest processing: download canvas images and optionally OCR them."""

from __future__ import annotations

import logging
from pathlib import Path

import httpx

from convmd.constants import DEFAULT_TIMEOUT, DOWNLOAD_TIMEOUT, USER_AGENT
from convmd.core import gemini
from convmd.core.http import get_client
from convmd.core.ocr import transcribe_image_with_gemini

logger = logging.getLogger(__name__)


def download_image(url: str, output_path: Path) -> None:
    """Download an image from a URL to the local filesystem."""
    with get_client(timeout=DOWNLOAD_TIMEOUT) as client:
        response = client.get(url, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        output_path.write_bytes(response.content)


def process_iiif_manifest(
    manifest_url: str,
    image_dir: Path,
    ocr_prompt: str | None = None,
    *,
    secondary_prompt: str | None = None,
) -> str:
    """Download all canvas images from a IIIF manifest and return Markdown.

    If a Gemini API key is configured and ``ocr_prompt`` is supplied, each image
    is also transcribed. When ``secondary_prompt`` is given (e.g. modern-language
    translation), it is appended as a second blockquote after the OCR result.
    """
    images_markdown = ""
    try:
        res = httpx.get(manifest_url, timeout=DEFAULT_TIMEOUT)
        res.raise_for_status()
        manifest_data = res.json()
    except Exception as e:
        logger.warning(f"Failed to process IIIF manifest from {manifest_url}: {e}")
        return ""

    sequences = manifest_data.get("sequences", [])
    if not sequences:
        return ""

    image_dir.mkdir(parents=True, exist_ok=True)
    canvases = sequences[0].get("canvases", [])
    logger.info(f"Found {len(canvases)} images in IIIF manifest.")

    do_ocr = gemini.is_configured()
    do_secondary = do_ocr and secondary_prompt is not None

    for i, canvas in enumerate(canvases):
        try:
            images = canvas.get("images", [])
            if not images:
                continue

            full_img_url = images[0]["resource"]["@id"]
            img_filename = f"page_{i + 1:04d}.jpg"
            img_path = image_dir / img_filename
            download_image(full_img_url, img_path)

            images_markdown += f"![[images/{img_filename}]]\n"

            if do_ocr:
                transcription = transcribe_image_with_gemini(img_path, prompt=ocr_prompt)
                if transcription:
                    images_markdown += "\n> " + transcription.replace("\n", "\n> ") + "\n\n"
                    if do_secondary and secondary_prompt is not None:
                        secondary = gemini.generate_text(
                            f"{secondary_prompt}\n\n{transcription}"
                        )
                        if secondary:
                            images_markdown += "> " + secondary.replace("\n", "\n> ") + "\n\n"

        except Exception as e:
            logger.warning(f"Failed to process image {i + 1}: {e}")

    return images_markdown
