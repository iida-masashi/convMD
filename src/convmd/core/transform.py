"""High-level Markdown transformation operations backed by Gemini."""

from __future__ import annotations

import logging
from pathlib import Path

from convmd.constants import Suffix
from convmd.core import gemini

logger = logging.getLogger(__name__)


_TRANSFORM_TEMPLATE = """\
以下のMarkdownファイルに対して、次の指示に従って内容を変換・処理してください。

【指示】
{instruction}

【重要なルール】
1. 画像リンク `![[images/...]]` やフロントマター（`---`で囲まれた部分）、元のレイアウト構造は可能な限り維持してください。
2. 余計な挨拶や「以下に出力します」などの会話文は一切出力せず、純粋なMarkdownファイルの中身だけを出力してください。
3. Markdownのコードブロック（```markdown など）では囲まず、そのままテキストとして出力してください。

【対象のファイル内容】
{text}
"""


_AUTO_LINK_INSTRUCTION = (
    "このMarkdown文章から重要な固有名詞、専門用語、または概念を抽出し、"
    "それらをObsidianの内部リンクフォーマットである `[[キーワード]]` に置き換えてください。"
    "また、文章全体を要約するような適切なタグ（例: `#マーケティング`, `#AI`）を3〜5個生成し、"
    "ファイルの末尾に追加してください。"
    "元の文章の意味や構造、既存の画像リンクなどは絶対に壊さないでください。"
)


_SUMMARY_TEMPLATE = """\
以下のテキストは、あるプロジェクトや調査に関連する複数のドキュメントを結合したものです。
全体を読み込み、内容を横断的に分析して、1ページの【統合サマリー（Executive Summary）】レポートをMarkdown形式で作成してください。

【重要なルール】
1. 全体の目的、主要な発見（ファインディングス）、およびネクストアクションが明確に伝わる構成にすること。
2. 見出しを活用して見やすく整理すること。
3. 余計な挨拶や会話文は一切出力せず、純粋なMarkdownの本文のみを出力すること。
4. Markdownのコードブロック（```markdown など）では囲まず、そのまま出力すること。

【対象のドキュメント群】
{text}
"""


_SUMMARY_INPUT_LIMIT = 500_000


def _run_and_save(prompt: str, out_path: Path, op_label: str) -> Path | None:
    text = gemini.generate_text(prompt)
    if text is None:
        return None
    out_path.write_text(text + "\n", encoding="utf-8")
    logger.info(f"{op_label} completed. Saved to: {out_path}")
    return out_path


def transform_markdown_with_gemini(file_path: Path, instruction: str) -> Path | None:
    """Apply an arbitrary instruction (translate/summarize/etc.) to a Markdown file."""
    if not gemini.is_configured():
        return None

    logger.info(f"Transforming {file_path.name} using Gemini API (Instruction: {instruction})...")
    prompt = _TRANSFORM_TEMPLATE.format(instruction=instruction, text=file_path.read_text(encoding="utf-8"))
    out_path = file_path.parent / f"{file_path.stem}{Suffix.TRANSFORMED}"
    return _run_and_save(prompt, out_path, "Transformation")


def apply_obsidian_links(file_path: Path) -> Path | None:
    """Auto-link important keywords as [[wikilinks]] and append tags."""
    if not gemini.is_configured():
        return None

    logger.info(f"Applying Obsidian Auto-Links to {file_path.name}...")
    prompt = _TRANSFORM_TEMPLATE.format(
        instruction=_AUTO_LINK_INSTRUCTION,
        text=file_path.read_text(encoding="utf-8"),
    )
    out_path = file_path.parent / f"{file_path.stem}{Suffix.LINKED}"
    return _run_and_save(prompt, out_path, "Auto-Linking")


def generate_executive_summary(text_contents: str, output_dir: Path) -> Path | None:
    """Produce a single executive summary across multiple Markdown documents."""
    if not gemini.is_configured():
        return None

    logger.info("Generating Executive Summary...")
    if len(text_contents) > _SUMMARY_INPUT_LIMIT:
        logger.warning("Combined text is too large. Truncating for summary generation.")
        text_contents = text_contents[:_SUMMARY_INPUT_LIMIT]

    prompt = _SUMMARY_TEMPLATE.format(text=text_contents)
    out_path = output_dir / Suffix.SUMMARY
    return _run_and_save(prompt, out_path, "Executive Summary")
