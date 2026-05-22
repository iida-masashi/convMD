"""Kokusho (国書データベース) classical book metadata + IIIF image extraction."""

from __future__ import annotations

import logging
from pathlib import Path

import httpx

from convmd.constants import DEFAULT_TIMEOUT
from convmd.core.iiif import process_iiif_manifest
from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)


_OCR_PROMPT = (
    "これは日本の古典籍（和古書や漢籍）の画像です。"
    "画像に書かれているテキストを正確に文字起こし（翻刻）してください。"
    "【重要な指示】\n"
    "1. 挨拶や「翻刻しました」等の会話文は一切出力しないでください。\n"
    "2. 「【右頁】」や「（右から左へ）」のようなレイアウトの解説、"
    "または「（虫損）」のような状態の注記は絶対に書かないでください。\n"
    "3. 元の書籍に書かれている漢字（および元の割注）だけを、純粋な平文として出力してください。"
)

_BILINGUAL_PROMPT = (
    "次の古典日本語/漢文の翻刻を、自然な現代日本語に訳してください。"
    "訳文のみ出力し、解説や注釈、会話文は一切付けないでください。"
)


def convert_kokusho(url: str, output_dir: Path, *, bilingual: bool = False, ocr: bool = False) -> Path | None:
    """Fetch a Kokusho biblio entry plus IIIF images (and optional OCR/translation)."""
    parts = [p for p in url.strip("/").split("/") if p]
    if "biblio" not in parts:
        logger.error(f"Invalid kokusho URL format: {url}")
        return None

    try:
        biblio_idx = parts.index("biblio")
        biblio_id = parts[biblio_idx + 1]
    except (ValueError, IndexError):
        logger.error(f"Could not extract biblio ID from: {url}")
        return None

    logger.info(f"Processing Kokusho Biblio ID: {biblio_id}")
    detail_api = f"https://kokusho.nijl.ac.jp/api/biblioDetail/{biblio_id}"
    manifest_api = f"https://kokusho.nijl.ac.jp/biblio/{biblio_id}/manifest"

    try:
        res = httpx.get(detail_api, timeout=DEFAULT_TIMEOUT)
        res.raise_for_status()
        detail_data = res.json()
    except Exception as e:
        logger.error(f"Failed to fetch detail data: {e}")
        return None

    title = detail_data.get("hshomeipdf", "") or detail_data.get(
        "hshomei", f"国書データベース_{biblio_id}"
    )
    safe_title = sanitize_filename(title)
    author = " ".join(detail_data.get("author", [])) or "不明"
    published = " ".join(detail_data.get("bpublish", []))
    satsu = detail_data.get("satsu", "")
    collection = detail_data.get("collection", "")

    image_dir = output_dir / safe_title / "images"
    logger.info(f"Fetching IIIF images for {title} (OCR enabled: {ocr})...")
    images_markdown = process_iiif_manifest(
        manifest_api,
        image_dir,
        ocr_prompt=_OCR_PROMPT if ocr else None,
        secondary_prompt=_BILINGUAL_PROMPT if bilingual else None,
    )

    frontmatter = generate_frontmatter(
        title,
        url,
        tags=["kokusho", "iiif", "web_clip"],
        author=author,
        extra={"biblio_id": biblio_id},
    )

    body = [
        f"# {title}\n\n",
        "## 書誌情報\n",
        f"- **著者**: {author}\n",
        f"- **出版/成立**: {published}\n",
        f"- **数量**: {satsu}\n",
        f"- **所蔵**: {collection}\n",
        f"- **URL**: {url}\n\n",
    ]

    if detail_data.get("chuki"):
        body.append("## 注記\n")
        for chuki in detail_data.get("chuki", []):
            body.append(f"- {chuki}\n")
        body.append("\n")

    if images_markdown:
        body.append("## 画像\n")
        body.append(images_markdown)

    md_content = frontmatter + "".join(body)

    output_dir.mkdir(parents=True, exist_ok=True)
    if image_dir.exists():
        md_path = output_dir / safe_title / f"{safe_title}.md"
    else:
        md_path = output_dir / f"{safe_title}.md"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    logger.info(f"Saved to {md_path}")
    return md_path
