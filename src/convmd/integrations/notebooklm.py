import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def upload_to_notebooklm(notebook_id: str, file_path: Path) -> None:
    """
    notebooklm-pyを利用して指定されたMarkdownファイルをNotebookLMにアップロードする。
    """
    try:
        from notebooklm_py import NotebookLMClient  # type: ignore
    except ImportError:
        logger.error(
            "notebooklm-py is not installed. Please install it using 'uv add notebooklm-py'"
        )
        return

    try:
        # クライアントの初期化 (ChromeやSafariのクッキー情報を自動で読み込みます)
        # ※事前の認証が必要です: `notebooklm login --browser-cookies chrome`
        client = NotebookLMClient()

        logger.info(f"Uploading {file_path.name} to NotebookLM (Notebook ID: {notebook_id})...")
        source = client.upload_file(notebook_id=notebook_id, file_path=str(file_path))
        logger.info(f"Successfully uploaded to NotebookLM. Source ID: {source.id}")
    except Exception as e:
        logger.error(f"Failed to upload to NotebookLM: {e}")
        logger.error(
            "Please ensure you have authenticated in your browser or run: notebooklm login --browser-cookies chrome"
        )
