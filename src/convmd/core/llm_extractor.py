"""LLM-based autonomous content extraction using Gemini 3."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel

from convmd.constants import Models
from convmd.core import gemini
from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "あなたはプロのWebコンテンツ抽出エージェントです。与えられたHTMLソース（またはテキスト）から、"
    "ナビゲーション、広告、フッターなどのノイズを完全に除去し、本質的なコンテンツのみを抽出してください。"
    "本文中の表やソースコード、数式などは正確にMarkdown記法で再現してください。"
)

# Used only when a caller passes a custom ``schema`` string: response_schema (below) constrains
# the model to exactly _ExtractedContent's fields, so a custom schema's extra fields must instead
# be requested via prompt and recovered by _parse_fallback's permissive JSON parsing.
_CUSTOM_SCHEMA_JSON_PROMPT = (
    "\n\n結果は以下のJSONフォーマットで出力してください：\n"
    "{\n"
    '  "title": "記事のタイトル",\n'
    '  "author": "著者名（不明な場合はnull）",\n'
    '  "date": "公開日（不明な場合はnull）",\n'
    '  "content_markdown": "抽出された本文（GitHub Flavored Markdown形式）",\n'
    '  "tags": ["関連タグのリスト"]\n'
    "}\n"
    "【カスタムスキーマ】\n以下の形式に従って追加情報を抽出してください：\n"
)


class _ExtractedContent(BaseModel):
    title: str | None = None
    author: str | None = None
    date: str | None = None
    content_markdown: str = ""
    tags: list[str] = []


def _parse_fallback(raw_text: str | None) -> _ExtractedContent | None:
    """Recover a result when ``response.parsed`` is unset (e.g. the model didn't honor the schema).

    Sometimes the LLM adds preamble/postamble even in JSON mode, so trim to the first/last brace.
    """
    if not raw_text:
        logger.error("LLM returned an empty response.")
        return None

    text = raw_text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            logger.error("No JSON block found in response.")
            return None
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON even after trimming: {e}")
            return None

    try:
        return _ExtractedContent.model_validate(data)
    except Exception as e:
        logger.error(f"Fallback JSON did not match expected schema: {e}")
        return None


def extract_with_llm(
    html_or_text: str,
    output_dir: Path,
    *,
    url: str | None = None,
    model: str = Models.GEMINI_FLASH,
    schema: str | None = None,
) -> Path | None:
    """Extract content using Gemini AI and save as a Markdown file."""
    logger.info(f"Starting LLM-based autonomous extraction (model={model})...")

    client = gemini.get_client()
    if not client:
        return None

    try:
        from google.genai import types

        # A custom schema asks the model for fields _ExtractedContent doesn't declare, so
        # response_schema (which strictly constrains output) must be skipped in that case.
        prompt = _SYSTEM_PROMPT
        if schema:
            prompt += _CUSTOM_SCHEMA_JSON_PROMPT + schema

        config = types.GenerateContentConfig(
            system_instruction=prompt,
            response_mime_type="application/json",
            response_schema=None if schema else _ExtractedContent,
            temperature=1.0,
            automatic_function_calling=gemini.NO_AFC,
        )

        response = client.models.generate_content(model=model, contents=html_or_text, config=config)
        gemini.usage_tracker().record(model, response)

        parsed = response.parsed if isinstance(response.parsed, _ExtractedContent) else None
        if parsed is None:
            parsed = _parse_fallback(response.text)
            if parsed is None:
                return None

        title = parsed.title or "Untitled AI Extract"
        content_markdown = parsed.content_markdown
        author = parsed.author
        date = parsed.date

        if not content_markdown:
            logger.warning("LLM extraction returned empty content_markdown.")
            return None

        # Clean up tags
        tags = [str(t) for t in parsed.tags if t]
        if "ai_extract" not in tags:
            tags.append("ai_extract")

        extra = {}
        if author:
            extra["author"] = author
        if date:
            extra["date"] = date

        frontmatter = generate_frontmatter(
            title=title,
            url=url or "",
            tags=tags,
            extra=extra,
        )

        full_markdown = f"{frontmatter}\n\n# {title}\n\n{content_markdown}"

        safe_title = sanitize_filename(title)
        output_path = output_dir / f"{safe_title}.md"

        # Ensure directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_text(full_markdown, encoding="utf-8")

        logger.info(f"Successfully extracted content via LLM: {output_path.name}")
        return output_path

    except Exception as e:
        logger.error(f"LLM autonomous extraction failed: {e}")
        return None
