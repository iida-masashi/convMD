"""Thin OCR wrapper over the centralized Gemini helper."""

from __future__ import annotations

import logging
from pathlib import Path

from convmd.core import gemini

logger = logging.getLogger(__name__)


def transcribe_image_with_gemini(image_path: Path, prompt: str | None = None) -> str:
    """Transcribe text from an image using Gemini Flash. Returns "" on failure."""
    if not gemini.is_configured():
        return ""
    logger.info(f"Running OCR on {image_path.name} using Gemini API...")
    return gemini.transcribe_image(image_path, prompt=prompt)
