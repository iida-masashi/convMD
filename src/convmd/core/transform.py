import logging
import os
from pathlib import Path
from typing import Optional

from google import genai

logger = logging.getLogger(__name__)


def transform_markdown_with_gemini(file_path: Path, instruction: str) -> Optional[Path]:
    """
    MarkdownファイルをGemini APIに送信し、指定された指示（翻訳、要約など）に従って
    内容を変換した新しいファイルを作成する。
    """
    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        logger.error(
            "API key not found. Please set GEMINI_API_KEY or GOOGLE_API_KEY environment variables."
        )
        return None

    logger.info(f"Transforming {file_path.name} using Gemini API (Instruction: {instruction})...")
    try:
        text = file_path.read_text(encoding="utf-8")

        prompt = f"""
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

        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        client = genai.Client(api_key=api_key, vertexai=False)

        # テキストの論理的な変換処理には、最も推論能力が高い Pro モデルを使用する
        response = client.models.generate_content(
            model="gemini-3.1-pro-preview",
            contents=prompt,
        )

        out_text = response.text.strip() if response.text else ""

        # 余分なコードブロック記号が付与された場合は除去する
        if out_text.startswith("```markdown"):
            out_text = out_text[11:]
        elif out_text.startswith("```"):
            out_text = out_text[3:]
        if out_text.endswith("```"):
            out_text = out_text[:-3]
        out_text = out_text.strip()

        # 保存先の決定 (例: 元ファイル名_transformed.md)
        out_path = file_path.parent / f"{file_path.stem}_transformed.md"
        out_path.write_text(out_text + "\n", encoding="utf-8")
        logger.info(f"Transformation completed. Saved to: {out_path}")
        return out_path

    except Exception as e:
        logger.error(f"Failed to transform {file_path.name}: {e}")
        return None


def apply_obsidian_links(file_path: Path) -> Optional[Path]:
    """
    MarkdownファイルをGemini APIに送信し、重要なキーワードをObsidianの内部リンク ([[ ]]) に変換し、
    ファイルの末尾に関連するタグ (#) を付与した新しいファイルを作成する。
    """
    instruction = (
        "このMarkdown文章から重要な固有名詞、専門用語、または概念を抽出し、それらをObsidianの内部リンクフォーマットである `[[キーワード]]` に置き換えてください。"
        "また、文章全体を要約するような適切なタグ（例: `#マーケティング`, `#AI`）を3〜5個生成し、ファイルの末尾に追加してください。"
        "元の文章の意味や構造、既存の画像リンクなどは絶対に壊さないでください。"
    )

    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        logger.error(
            "API key not found. Please set GEMINI_API_KEY or GOOGLE_API_KEY environment variables."
        )
        return None

    logger.info(f"Applying Obsidian Auto-Links to {file_path.name}...")
    try:
        text = file_path.read_text(encoding="utf-8")

        prompt = f"""
以下のMarkdownファイルに対して、次の指示に従って内容を変換・処理してください。

【指示】
{instruction}

【重要なルール】
1. 画像リンク `![[images/...]]` やフロントマター（`---`で囲まれた部分）、元のレイアウト構造は可能な限り維持してください。
2. 余計な挨拶や会話文は一切出力せず、純粋なMarkdownファイルの中身だけを出力してください。
3. Markdownのコードブロック（```markdown など）では囲まず、そのままテキストとして出力してください。

【対象のファイル内容】
{text}
"""

        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        client = genai.Client(api_key=api_key, vertexai=False)

        response = client.models.generate_content(
            model="gemini-3.1-pro-preview",
            contents=prompt,
        )

        out_text = response.text.strip() if response.text else ""

        if out_text.startswith("```markdown"):
            out_text = out_text[11:]
        elif out_text.startswith("```"):
            out_text = out_text[3:]
        if out_text.endswith("```"):
            out_text = out_text[:-3]
        out_text = out_text.strip()

        out_path = file_path.parent / f"{file_path.stem}_linked.md"
        out_path.write_text(out_text + "\n", encoding="utf-8")
        logger.info(f"Auto-Linking completed. Saved to: {out_path}")
        return out_path

    except Exception as e:
        logger.error(f"Failed to apply auto-links to {file_path.name}: {e}")
        return None


def generate_executive_summary(text_contents: str, output_dir: Path) -> Optional[Path]:
    """
    複数のMarkdownファイルから集約したテキストを基に、統合サマリーを生成する。
    """
    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        logger.error(
            "API key not found. Please set GEMINI_API_KEY or GOOGLE_API_KEY environment variables."
        )
        return None

    logger.info("Generating Executive Summary...")
    try:
        # トークン数の安全マージンとして文字数を制限する（Proモデルは1Mトークンまで対応可能なので大きめに取るが、一旦安全のため50万文字程度に制限）
        # 実際の運用ではトークン計算が必要
        if len(text_contents) > 500000:
            logger.warning("Combined text is too large. Truncating for summary generation.")
            text_contents = text_contents[:500000]

        prompt = f"""
以下のテキストは、あるプロジェクトや調査に関連する複数のドキュメントを結合したものです。
全体を読み込み、内容を横断的に分析して、1ページの【統合サマリー（Executive Summary）】レポートをMarkdown形式で作成してください。

【重要なルール】
1. 全体の目的、主要な発見（ファインディングス）、およびネクストアクションが明確に伝わる構成にすること。
2. 見出しを活用して見やすく整理すること。
3. 余計な挨拶や会話文は一切出力せず、純粋なMarkdownの本文のみを出力すること。
4. Markdownのコードブロック（```markdown など）では囲まず、そのまま出力すること。

【対象のドキュメント群】
{text_contents}
"""

        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        client = genai.Client(api_key=api_key, vertexai=False)

        response = client.models.generate_content(
            model="gemini-3.1-pro-preview",
            contents=prompt,
        )

        out_text = response.text.strip() if response.text else ""

        if out_text.startswith("```markdown"):
            out_text = out_text[11:]
        elif out_text.startswith("```"):
            out_text = out_text[3:]
        if out_text.endswith("```"):
            out_text = out_text[:-3]
        out_text = out_text.strip()

        out_path = output_dir / "executive_summary.md"
        out_path.write_text(out_text + "\n", encoding="utf-8")
        logger.info(f"Executive Summary completed. Saved to: {out_path}")
        return out_path

    except Exception as e:
        logger.error(f"Failed to generate executive summary: {e}")
        return None
