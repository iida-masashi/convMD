"""High-level Markdown transformation operations backed by Gemini."""

from __future__ import annotations

import logging
import re
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
    "また、文章全体を要約するような適切なタグ（例: `歴史`, `AI`）を3〜5個生成し、"
    "出力するファイルの最後の一行に `TAGS: タグ1, タグ2` の形式で出力してください。\n"
    "【厳守】\n"
    "元の文章の意味、改行、見出し、画像リンク、フロントマターなどは絶対に壊さないでください。"
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


def apply_obsidian_links(
    file_path: Path,
    *,
    vault_path: Path | None = None,
    tag_similarity_cutoff: float = 0.85,
) -> Path | None:
    """Auto-link important keywords as [[wikilinks]] and inject tags.

    When ``vault_path`` is provided, generated tags are normalized against the
    set of tags already present in the vault before being injected.
    """
    if not gemini.is_configured():
        return None

    logger.info(f"Applying Obsidian Auto-Links to {file_path.name}...")
    original_content = file_path.read_text(encoding="utf-8")
    prompt = _TRANSFORM_TEMPLATE.format(
        instruction=_AUTO_LINK_INSTRUCTION,
        text=original_content,
    )
    out_path = file_path.parent / f"{file_path.stem}{Suffix.LINKED}"

    text = gemini.generate_text(prompt)
    if text is None:
        return None

    # Extract tags from the end
    tags = []
    lines = text.strip().split('\n')
    if lines and lines[-1].startswith('TAGS:'):
        tag_line = lines.pop()
        raw_tags = tag_line.replace('TAGS:', '').split(',')
        tags = [t.strip() for t in raw_tags if t.strip()]
        text = '\n'.join(lines)

    if tags and vault_path is not None:
        from convmd.integrations.vault_tags import normalize_tags, scan_vault_tags

        existing = scan_vault_tags(vault_path)
        tags = normalize_tags(tags, existing, cutoff=tag_similarity_cutoff)

    # Inject tags into frontmatter
    if tags:
        # We need to inject tags properly into YAML array format
        tag_yaml_items = [f'  - "{t}"' for t in tags]
        tag_yaml_block = "\n".join(tag_yaml_items) + "\n"

        # Simple injection assuming basic YAML format
        # Case 1: tags array already exists
        if "tags:\n" in text:
            text = re.sub(r'(tags:\n(?:[ \t]+-[^\n]*\n)*)', r'\1' + tag_yaml_block, text, count=1)
        # Case 2: frontmatter exists but no tags array yet
        elif "---\n" in text:
            text = text.replace("---\n", f"---\ntags:\n{tag_yaml_block}", 1)

    out_path.write_text(text + "\n", encoding="utf-8")
    logger.info(f"Auto-Linking completed. Saved to: {out_path}")
    return out_path


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
