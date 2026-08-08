import logging
import re
from pathlib import Path

import anydoc
from markitdown import MarkItDown

from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)

# Thresholds picked from measured separation between known-garbled PDF extractions
# (a Type1-subset-font PDF with a broken/absent ToUnicode map) and every negative set
# on hand: known-good .md outputs already in output/ (English prose, Japanese prose,
# table-heavy, formula-heavy), plus synthetic accented-Latin prose and punctuation
# (French/German/Portuguese/Spanish, incl. guillemets and German section-sign legal
# citations) that a naive range check would misflag. After excluding the symbols below,
# the garbled sample scored weird_ratio=0.037 and cid_ratio=0.717; every negative-set
# sample scored weird_ratio=0.0 and cid_ratio<=0.012. Either signal alone catches one
# engine's failure mode (anydoc emits raw glyph-substitution symbols; MarkItDown emits
# literal "(cid:N)" tokens when a PDF's embedded font has no usable ToUnicode map), so
# both are checked and either tripping counts as garbled.
_CID_TOKEN_RE = re.compile(r"\(cid:\d+\)")
_WEIRD_RATIO_THRESHOLD = 0.02
_CID_RATIO_THRESHOLD = 0.1

# Latin-1 punctuation/symbol block (U+00A0-00BF) rather than all of Latin-1 Supplement:
# accented letters (U+00C0-00FF, e.g. é/è/ü/ö/ã/ç) are excluded because French/German/
# Portuguese/etc. prose uses them at 5-15% density -- well above what a range covering
# them would tolerate. Within U+00A0-00BF, symbols with ordinary technical, financial,
# or language-specific use are excluded individually: degree/currency/math signs, the
# Spanish inverted question/exclamation marks, French/German guillemet quotation marks
# (« » — French dialogue and German block quotes run these densely), and the German
# section sign (§ — dense in legal/academic citations, e.g. "§ 823 BGB").
_WEIRD_RANGE_EXCEPTIONS = set("°£¥¢¤±ª¿¡«»§")


def _is_garbled(text: str) -> bool:
    """Heuristic check for mojibake from a PDF with a broken embedded-font ToUnicode map.

    Not a general-purpose language/encoding detector: it only targets the two failure
    signatures observed from anydoc and MarkItDown on such PDFs (see thresholds above).
    Empty text is a different failure (no text layer, i.e. a scanned image PDF) and is
    reported separately by the caller rather than folded into this check.
    """
    stripped = text.strip()
    if not stripped:
        return False

    # Character-based, not word-count-based: whitespace-poor Japanese/Chinese text can
    # have a word count near 1 (str.split() has nothing to split on), which would make
    # even a single stray "(cid:N)" token score as 100% garbled.
    cid_chars = sum(len(m) for m in _CID_TOKEN_RE.findall(stripped))
    if cid_chars / len(stripped) >= _CID_RATIO_THRESHOLD:
        return True

    weird_count = sum(
        1
        for ch in stripped
        if (0x02B0 <= ord(ch) <= 0x02FF or 0x00A0 <= ord(ch) <= 0x00BF)
        and ch not in _WEIRD_RANGE_EXCEPTIONS
    )
    weird_ratio = weird_count / len(stripped)
    return weird_ratio >= _WEIRD_RATIO_THRESHOLD


def _convert_to_markdown_text(file_path: Path) -> str | None:
    """Return extracted Markdown text, or None if every engine produced mojibake or empty text.

    anydoc is faster and produces cleaner tables, but can't OCR scanned PDFs or
    handle encrypted files; MarkItDown covers those cases. Neither engine raises
    on a PDF whose embedded font has a broken/absent ToUnicode map — both silently
    return garbled text — so the result is checked with _is_garbled() after each attempt.
    """
    try:
        text = anydoc.to_markdown(str(file_path))
        if text.strip() and not _is_garbled(text):
            return text
        reason = "no text" if not text.strip() else "garbled text"
        logger.warning(f"anydoc produced {reason} for {file_path.name}; trying MarkItDown")
    except anydoc.ConvertError as e:
        logger.info(f"anydoc could not convert {file_path.name} ({e}); falling back to MarkItDown")

    md_engine = MarkItDown()
    result = md_engine.convert(str(file_path))
    text = str(result.text_content)
    if not text.strip():
        logger.error(
            f"MarkItDown returned no text for {file_path.name}; this looks like a "
            "scanned image PDF with no text layer. Text extraction cannot recover "
            "this file; OCR is required."
        )
        return None
    if _is_garbled(text):
        logger.error(
            f"MarkItDown produced garbled text for {file_path.name}; "
            "the embedded font's ToUnicode map is likely broken or missing. "
            "Text extraction cannot recover this file; OCR is required."
        )
        return None
    return text


def convert_office_file(
    file_path: Path,
    output_dir: Path,
    *,
    ai_extract: bool = False,
    schema: str | None = None,
) -> Path | None:
    """
    Converts local Office files (PPTX, XLSX, DOCX, PDF, etc.) to Markdown
    using anydoc (falling back to MarkItDown when unsupported).
    """
    logger.info(f"Attempting to convert {file_path}...")

    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return None

    try:
        md_content = _convert_to_markdown_text(file_path)
        if md_content is None:
            # _convert_to_markdown_text already logged the reason (garbled output
            # from every available engine, likely a broken embedded-font ToUnicode map).
            return None

        if ai_extract:
            from convmd.core.llm_extractor import extract_with_llm

            logger.info(f"Applying AI autonomous extraction to {file_path.name} content...")
            return extract_with_llm(
                md_content,
                output_dir,
                url=str(file_path.resolve()),
                schema=schema,
            )

        safe_title = sanitize_filename(file_path.stem)
        filename = f"{safe_title}.md"
        out_path = output_dir / filename

        frontmatter = generate_frontmatter(
            title=file_path.name, url=str(file_path.resolve()), tags=["local_file", "office"]
        )

        out_path.write_text(frontmatter + md_content, encoding="utf-8")

        logger.info(f"Successfully converted {file_path} to {out_path}")
        return out_path
    except Exception as e:
        logger.error(f"Failed to convert {file_path}: {e}")
        return None
