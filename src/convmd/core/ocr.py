import logging
import os
from pathlib import Path

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

def transcribe_image_with_gemini(image_path: Path, prompt: str | None = None) -> str:
    """
    画像をGemini APIに送信し、文字起こし（OCR）を取得する。
    APIキーが設定されていない場合はスキップする。
    """
    # APIキーの存在確認
    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        return ""

    logger.info(f"Running OCR on {image_path.name} using Gemini API...")
    try:
        # APIキーは環境変数から自動で読み込まれます
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        # Initialize client explicitly with API key to bypass Vertex AI auto-discovery issues
        client = genai.Client(api_key=api_key, vertexai=False)
        
        from PIL import Image
        
        if prompt is None:
            prompt = (
                "画像に書かれているテキストを正確に文字起こししてください。"
                "レイアウトや読み順に従い、そのままの文字で出力してください。"
                "文字以外の部分（シミや汚れ、図形など）は無視し、テキストのみを出力してください。"
            )
        
        img = Image.open(image_path)
        
        # アップロードと解析の実行
        # google-genai は PIL.Image を直接 contents に渡すことができます
        response = client.models.generate_content(
            model="gemini-3-flash-preview", # 高速かつ高精度なFlashモデルを利用
            contents=[img, prompt]
        )
        
        # 上記がうまく動かない場合は、直接ファイルをアップロードする方式にフォールバック
        return response.text.strip()
    except Exception as e:
        logger.warning(f"Failed OCR for {image_path.name}: {e}")
        return ""
