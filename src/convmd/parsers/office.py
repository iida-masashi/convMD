import logging
from pathlib import Path

from markitdown import MarkItDown

from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)


def convert_office_file(
    file_path: Path,
    output_dir: Path,
    *,
    ai_extract: bool = False,
    schema: str | None = None,
) -> Path | None:
    """
    Converts local Office files (PPTX, XLSX, DOCX, PDF, etc.) to Markdown using MarkItDown.
    """
    logger.info(f"Attempting to convert {file_path} using MarkItDown...")

    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return None

    try:
        md_engine = MarkItDown()
        result = md_engine.convert(str(file_path))
        md_content = result.text_content

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
