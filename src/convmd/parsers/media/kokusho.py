import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from convmd.core.utils import sanitize_filename
from convmd.core.iiif import process_iiif_manifest

logger = logging.getLogger(__name__)

def convert_kokusho(url: str, output_dir: Path) -> None:
    """国文学研究資料館の国書データベースの書籍データと画像を抽出する"""
    # 1. biblio_idを抽出する
    # 例: https://kokusho.nijl.ac.jp/biblio/100243699/
    parts = [p for p in url.strip("/").split("/") if p]
    if "biblio" not in parts:
        logger.error(f"Invalid kokusho URL format: {url}")
        return
        
    try:
        biblio_idx = parts.index("biblio")
        biblio_id = parts[biblio_idx + 1]
    except (ValueError, IndexError):
        logger.error(f"Could not extract biblio ID from: {url}")
        return

    logger.info(f"Processing Kokusho Biblio ID: {biblio_id}")
    
    # 2. APIエンドポイントの設定
    detail_api = f"https://kokusho.nijl.ac.jp/api/biblioDetail/{biblio_id}"
    manifest_api = f"https://kokusho.nijl.ac.jp/biblio/{biblio_id}/manifest"

    # 3. 書誌情報の取得
    try:
        res = httpx.get(detail_api, timeout=10.0)
        res.raise_for_status()
        detail_data = res.json()
    except Exception as e:
        logger.error(f"Failed to fetch detail data: {e}")
        return

    # タイトルの取得
    title = detail_data.get("hshomeipdf", "名称不明")
    if not title:
        title = detail_data.get("hshomei", f"国書データベース_{biblio_id}")
        
    safe_title = sanitize_filename(title)
    
    # 著者などの情報を整形
    author = " ".join(detail_data.get("author", [])) or "不明"
    published = " ".join(detail_data.get("bpublish", []))
    satsu = detail_data.get("satsu", "")
    collection = detail_data.get("collection", "")
    
    # 4. 画像マニフェスト(IIIF)の取得と画像ダウンロード
    image_dir = output_dir / safe_title / "images"
    ocr_prompt = (
        "これは日本の古典籍（和古書や漢籍）の画像です。"
        "画像に書かれているテキストを正確に文字起こし（翻刻）してください。"
        "【重要な指示】\n"
        "1. 挨拶や「翻刻しました」等の会話文は一切出力しないでください。\n"
        "2. 「【右頁】」や「（右から左へ）」のようなレイアウトの解説、または「（虫損）」のような状態の注記は絶対に書かないでください。\n"
        "3. 元の書籍に書かれている漢字（および元の割注）だけを、純粋な平文として出力してください。"
    )
    images_markdown = process_iiif_manifest(manifest_api, image_dir, ocr_prompt=ocr_prompt)

    # 5. Markdownテキストの構築
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    md_content = f"""---
title: "{title}"
author: "{author}"
source: "{url}"
biblio_id: "{biblio_id}"
date: {current_time}
tags: [kokusho, iiif, web_clip]
---

# {title}

## 書誌情報
- **著者**: {author}
- **出版/成立**: {published}
- **数量**: {satsu}
- **所蔵**: {collection}
- **URL**: {url}

"""
    if detail_data.get("chuki"):
        md_content += "## 注記\n"
        for chuki in detail_data.get("chuki", []):
            md_content += f"- {chuki}\n"
        md_content += "\n"

    if images_markdown:
        md_content += "## 画像\n"
        md_content += images_markdown

    # 6. 保存処理
    output_dir.mkdir(parents=True, exist_ok=True)
    # 画像がある場合はフォルダ内にmdを保存し、ない場合は直下に保存
    if image_dir.exists():
        md_path = output_dir / safe_title / f"{safe_title}.md"
    else:
        md_path = output_dir / f"{safe_title}.md"
        
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    logger.info(f"Saved to {md_path}")
