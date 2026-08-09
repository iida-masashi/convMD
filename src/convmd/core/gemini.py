"""Centralized Gemini API helper.

Wraps API-key resolution, client construction, code-fence stripping, and usage tracking
so callers (transform.py, ocr.py, kokusho bilingual, future RAG) just supply a prompt.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from google import genai

from convmd.constants import Models

logger = logging.getLogger(__name__)


def get_api_key() -> str | None:
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def is_configured() -> bool:
    return get_api_key() is not None


def get_client() -> Any | None:
    """Return a genai.Client or None if API key not configured."""
    api_key = get_api_key()
    if not api_key:
        logger.error(
            "API key not found. Please set GEMINI_API_KEY or GOOGLE_API_KEY environment variables."
        )
        return None
    return genai.Client(api_key=api_key, vertexai=False)


def strip_code_fence(text: str) -> str:
    """Remove a leading ```markdown / ``` fence and a trailing ``` fence, if present."""
    out = text.strip()
    if out.startswith("```markdown"):
        out = out[len("```markdown") :]
    elif out.startswith("```"):
        out = out[3:]
    if out.endswith("```"):
        out = out[:-3]
    return out.strip()


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    calls: int = 0


@dataclass
class UsageTracker:
    """Process-wide token usage accumulator. One entry per model."""

    by_model: dict[str, Usage] = field(default_factory=dict)

    def record(self, model: str, response: Any) -> None:
        usage = self.by_model.setdefault(model, Usage())
        usage.calls += 1
        meta = getattr(response, "usage_metadata", None)
        if meta is None:
            return
        prompt = getattr(meta, "prompt_token_count", None) or getattr(meta, "input_tokens", 0) or 0
        out = (
            getattr(meta, "candidates_token_count", None)
            or getattr(meta, "output_tokens", 0)
            or 0
        )
        thoughts = getattr(meta, "thoughts_token_count", None) or 0
        usage.input_tokens += int(prompt)
        usage.output_tokens += int(out) + int(thoughts)

    def is_empty(self) -> bool:
        return not self.by_model


_tracker = UsageTracker()


def usage_tracker() -> UsageTracker:
    return _tracker


def reset_usage() -> None:
    _tracker.by_model.clear()


def generate_text(prompt: str, *, model: str = Models.GEMINI_PRO) -> str | None:
    """Send a prompt to Gemini and return the cleaned text, or None on failure."""
    client = get_client()
    if client is None:
        return None
    try:
        response = client.models.generate_content(model=model, contents=prompt)
        _tracker.record(model, response)
        raw = response.text if response.text else ""
        return strip_code_fence(raw)
    except Exception as e:
        logger.error(f"Gemini text generation failed (model={model}): {e}")
        return None


def transcribe_image(
    image_path: Path,
    prompt: str | None = None,
    *,
    model: str = Models.GEMINI_FLASH,
) -> str:
    """Run OCR on an image via Gemini. Returns empty string on failure (matches legacy behavior)."""
    client = get_client()
    if client is None:
        return ""
    try:
        from PIL import Image

        img = Image.open(image_path)
        default_prompt = (
            "この画像のテキストを正確に文字起こしして。会話文や注記は不要。本文のみ。"
        )
        response = client.models.generate_content(
            model=model,
            contents=[prompt or default_prompt, img],
        )
        _tracker.record(model, response)
        return response.text.strip() if response.text else ""
    except Exception as e:
        logger.error(f"Gemini image transcription failed for {image_path.name}: {e}")
        return ""
