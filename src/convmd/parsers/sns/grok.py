"""X/Twitter timeline extractor via the xAI Grok Agent Tools API (x_search).

The legacy public syndication endpoint (see ``twitter.py``) now returns HTTP 429,
so this parser fetches a user's recent posts through Grok's ``x_search`` tool.
Grok returns the posts as one prose blob (delimited by ``**投稿日:**``) plus
``annotations`` carrying the source status URLs. Because the post text is
reproduced *by the model* (not a structured per-post field), the raw API
response is persisted alongside the Markdown and the output is tagged as
AI-mediated requiring verification.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from convmd.core.http import get_client
from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)

XAI_RESPONSES_URL = "https://api.x.ai/v1/responses"
XAI_MODEL = "grok-4.3"
XAI_TIMEOUT = 240.0


def fetch_grok_posts(screen_name: str) -> dict[str, Any] | None:
    """Fetch a user's recent X posts verbatim via Grok's x_search tool.

    Returns the parsed ``/v1/responses`` JSON, or None on failure.
    """
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        logger.error("XAI_API_KEY not set. Cannot reach the xAI Grok API.")
        return None

    prompt = (
        f"@{screen_name} の最近の投稿を、できる限り多く、最低でも30件、列挙してください。"
        "各投稿について、投稿日時・本文（原文のまま逐語で、要約・添削・補完を一切せず）・"
        "投稿URLを付けてください。本文は誤字も含め原文を忠実に再現してください。"
    )
    payload = {
        "model": XAI_MODEL,
        "input": [{"role": "user", "content": prompt}],
        "tools": [{"type": "x_search", "allowed_x_handles": [screen_name]}],
    }

    logger.info(f"Fetching posts for @{screen_name} via Grok x_search...")
    try:
        with get_client(timeout=XAI_TIMEOUT) as client:
            response = client.post(
                XAI_RESPONSES_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
    except Exception as e:
        logger.error(f"Failed to fetch posts for @{screen_name}: {e}")
        return None

    return data


def _extract_message_text(data: dict[str, Any]) -> str:
    """Concatenate the text of any ``message`` items in the responses output."""
    text = ""
    for item in data.get("output", []):
        if item.get("type") == "message":
            for content in item.get("content", []):
                text += content.get("text", "")
    return text


def convert_grok(screen_name: str, output_dir: Path) -> Path | None:
    data = fetch_grok_posts(screen_name)
    if not data:
        return None

    text = _extract_message_text(data)
    if not text.strip():
        logger.info(f"Grok returned no post text for @{screen_name}.")
        return None

    safe_name = sanitize_filename(screen_name)

    # Persist the raw API response as the source-of-truth anchor (改変リスク対策).
    raw_path = output_dir / f"{safe_name}_grok_raw.json"
    raw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Saved raw Grok response to {raw_path}")

    cost_usd = data.get("usage", {}).get("cost_in_usd_ticks", 0) / 1e9

    frontmatter = generate_frontmatter(
        title=f"@{screen_name} の投稿まとめ（Grok x_search 取得）",
        url=f"https://x.com/{screen_name}",
        tags=["sns", "twitter", "grok", screen_name],
        extra={"evidence_type": "ai_mediated", "source_tool": "xai_grok_x_search"},
    )

    callout = (
        "> [!warning] 要検証\n"
        "> 本文は xAI Grok の `x_search` ツールが再現したテキストであり、"
        "AI を介した複製です。投稿の取りこぼし・改変の可能性があるため、"
        "引用前に各投稿の URL で原典を確認してください。"
        f"生レスポンスは `{raw_path.name}` に保存しています。\n\n"
    )

    md_path = output_dir / f"{safe_name}_grok.md"
    body = f"{frontmatter}# @{screen_name} の投稿まとめ\n\n{callout}---\n\n{text.strip()}\n"
    md_path.write_text(body, encoding="utf-8")
    logger.info(f"Saved Grok posts to {md_path} (cost ${cost_usd:.4f})")
    return md_path
