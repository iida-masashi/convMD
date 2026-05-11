import logging
from pathlib import Path

from markdownify import markdownify as md
from readability import Document  # type: ignore

from convmd.core.download import fetch_html, process_images
from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)

def convert_general_website(url: str, output_dir: Path) -> Path | None:
    """
    Fetches a general URL, extracts main content via Readability,
    and saves it as a Markdown file with local images.
    """
    logger.info(f"Processing {url} with Readability engine...")
    html = fetch_html(url)
    if not html:
        logger.error(f"Failed to retrieve HTML for {url}")
        return None

    # Extract main content
    doc = Document(html)
    title = doc.title()
    summary_html = doc.summary()

    # Convert HTML to Markdown
    md_body = md(summary_html, heading_style="ATX")

    # Download images and update links
    logger.info("Downloading images and updating links...")
    md_body = process_images(md_body, url, output_dir)

    # Generate frontmatter
    frontmatter = generate_frontmatter(title, url, tags=["web_clip", "general"])

    # Generate filename and path
    safe_title = sanitize_filename(title)
    filename = f"{safe_title}.md"
    file_path = output_dir / filename

    # Save the file
    file_path.write_text(frontmatter + md_body, encoding="utf-8")

    logger.info(f"Saved to {file_path}")
    return file_path
