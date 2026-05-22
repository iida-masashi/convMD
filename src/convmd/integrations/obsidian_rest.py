import logging
import urllib.parse
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

def export_to_obsidian_api(file_path: Path, api_url: str, token: str, target_folder: str = "Inbox") -> bool:
    """Export a Markdown file directly to Obsidian via Local REST API."""
    if not file_path.exists():
        return False

    try:
        content = file_path.read_bytes()
        encoded_folder = urllib.parse.quote(target_folder.strip('/'))
        encoded_filename = urllib.parse.quote(file_path.name)

        url = f"{api_url.rstrip('/')}/vault/{encoded_folder}/{encoded_filename}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "text/markdown"
        }

        # Local REST API requires HTTPS and self-signed certs are common
        with httpx.Client(verify=False) as client:
            response = client.put(url, headers=headers, content=content, timeout=10.0)
            response.raise_for_status()

        logger.info(f"Successfully exported {file_path.name} to Obsidian Vault via API.")
        return True
    except Exception as e:
        logger.error(f"Failed to export to Obsidian API: {e}")
        return False
