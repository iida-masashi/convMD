import logging
import urllib.parse
import webbrowser
from pathlib import Path

logger = logging.getLogger(__name__)


def open_in_obsidian(vault_path: Path) -> None:
    """
    指定されたパスをVault名としてObsidianアプリを起動します。
    """
    try:
        vault_name = vault_path.name
        encoded_vault = urllib.parse.quote(vault_name)
        uri = f"obsidian://open?vault={encoded_vault}"
        logger.info(f"Opening Obsidian vault: {vault_name}")
        webbrowser.open(uri)
    except Exception as e:
        logger.error(f"Failed to open Obsidian: {e}")
