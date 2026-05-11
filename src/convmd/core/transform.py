import logging
import os
from pathlib import Path

from google import genai

logger = logging.getLogger(__name__)

def transform_markdown_with_gemini(file_path: Path, instruction: str) -> None:
    """
    MarkdownファイルをGemini APIに送信し、指定された指示（翻訳、要約など）に従って
    内容を変換した新しいファイルを作成する。
    """
    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        logger.error("API key not found. Please set GEMINI_API_KEY or GOOGLE_API_KEY environment variables.")
        return

    logger.info(f"Transforming {file_path.name} using Gemini API (Instruction: {instruction})...")
    try:
        text = file_path.read_text(encoding='utf-8')
        
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

        out_text = response.text.strip()
        
        # 余分なコードブロック記号が付与された場合は除去する
        if out_text.startswith('```markdown'):
            out_text = out_text[11:]
        elif out_text.startswith('```'):
            out_text = out_text[3:]
        if out_text.endswith('```'):
            out_text = out_text[:-3]
        out_text = out_text.strip()

        # 保存先の決定 (例: 元ファイル名_transformed.md)
        out_path = file_path.parent / f"{file_path.stem}_transformed.md"
        out_path.write_text(out_text + '\n', encoding='utf-8')
        logger.info(f"Transformation completed. Saved to: {out_path}")
        
    except Exception as e:
        logger.error(f"Failed to transform {file_path.name}: {e}")
