"""LLM-based autonomous content extraction using Gemini 3."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from convmd.constants import Models
from convmd.core import gemini
from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "あなたはプロのWebコンテンツ抽出エージェントです。与えられたHTMLソース（またはテキスト）から、"
    "ナビゲーション、広告、フッターなどのノイズを完全に除去し、本質的なコンテンツのみを抽出してください。"
    "結果は以下のJSONフォーマットで出力してください：\n"
    "{\n"
    "  \"title\": \"記事のタイトル\",\n"
    "  \"author\": \"著者名（不明な場合はnull）\",\n"
    "  \"date\": \"公開日（不明な場合はnull）\",\n"
    "  \"content_markdown\": \"抽出された本文（GitHub Flavored Markdown形式）\",\n"
    "  \"tags\": [\"関連タグのリスト\"]\n"
    "}\n"
    "【注記】本文中の表やソースコード、数式などは正確にMarkdown記法で再現してください。"
)


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

        prompt = _SYSTEM_PROMPT
        if schema:
            prompt += f"\n\n【カスタムスキーマ】\n以下の形式に従って追加情報を抽出してください：\n{schema}"

        config = types.GenerateContentConfig(
            system_instruction=prompt,
            response_mime_type="application/json",
            temperature=1.0,
        )

        response = client.models.generate_content(model=model, contents=html_or_text, config=config)
        gemini.usage_tracker().record(model, response)

        if not response.text:
            logger.error("LLM returned an empty response.")
            return None

        # Robust JSON parsing: sometimes LLM adds preamble/postamble even in JSON mode
        raw_text = response.text.strip()
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            # Try to find the first '{' and last '}'
            start = raw_text.find("{")
            end = raw_text.rfind("}")
            if start != -1 and end != -1:
                try:
                    data = json.loads(raw_text[start : end + 1])
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON even after trimming: {e}")
                    return None
            else:
                logger.error("No JSON block found in response.")
                return None

        title = data.get("title") or "Untitled AI Extract"
        content_markdown = data.get("content_markdown", "")
        author = data.get("author")
        date = data.get("date")
        tags = data.get("tags", [])

        if not content_markdown:
            logger.warning("LLM extraction returned empty content_markdown.")
            return None

        # Clean up tags
        tags = [str(t) for t in tags if t]
        if "ai_extract" not in tags:
            tags.append("ai_extract")

        extra = {}
        if author:
            extra["author"] = author
        if date:
            extra["date"] = date

        frontmatter = generate_frontmatter(
            title=title,
            url=url,
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
