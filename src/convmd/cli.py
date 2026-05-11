import argparse
import logging
import shutil
import time
from pathlib import Path
from typing import List
from urllib.parse import urlparse

from convmd.config import get_output_dir
from convmd.core.transform import transform_markdown_with_gemini
from convmd.integrations.notebooklm import upload_to_notebooklm
from convmd.integrations.obsidian import open_in_obsidian
from convmd.parsers.general import convert_general_website
from convmd.parsers.media.audio import convert_audio_file
from convmd.parsers.media.kokusho import convert_kokusho
from convmd.parsers.media.qiita import convert_qiita
from convmd.parsers.media.wikipedia import convert_wikipedia
from convmd.parsers.media.zenn import convert_zenn
from convmd.parsers.office import convert_office_file
from convmd.parsers.sns.note import convert_note_com
from convmd.parsers.sns.twitter import convert_twitter
from convmd.parsers.sns.youtube import convert_youtube

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def process_target(target_str: str, target_path: Path, output_dir: Path) -> None:
    """Processes a single target URL or file safely, catching exceptions."""
    try:
        # Check if target is a local file
        if target_path.exists() and target_path.is_file():
            logger.info(f"Processing local file: {target_path}")

            # If it's already a markdown file, just copy it to output_dir to trigger the pipeline
            if target_path.suffix.lower() == ".md":
                dest_path = output_dir / target_path.name
                if target_path.resolve() != dest_path.resolve():
                    shutil.copy2(target_path, dest_path)
                    logger.info(f"Copied markdown file to {dest_path}")
                return

            # Route to audio transcriber if it's an audio/video file
            audio_extensions = {".mp3", ".wav", ".m4a", ".mp4", ".flac", ".ogg", ".aac"}
            if target_path.suffix.lower() in audio_extensions:
                convert_audio_file(target_path, output_dir)
                return

            # Otherwise route to office/markitdown parser
            convert_office_file(target_path, output_dir)
            return

        # Treat as URL
        logger.info(f"Analyzing URL: {target_str}")
        parsed_url = urlparse(target_str)
        domain = parsed_url.netloc

        if "note.com" in domain:
            parts = parsed_url.path.strip("/").split("/")
            if len(parts) == 1:
                logger.info("Detected note.com creator profile. Fetching all notes...")
                convert_note_com(parts[0], output_dir)
                return

        if "x.com" in domain or "twitter.com" in domain:
            parts = parsed_url.path.strip("/").split("/")
            if len(parts) >= 1:
                screen_name = parts[0]
                logger.info(f"Detected X.com account: @{screen_name}. Fetching recent tweets...")
                convert_twitter(screen_name, output_dir)
                return

        if "youtube.com" in domain or "youtu.be" in domain:
            logger.info("Detected YouTube video. Extracting transcript...")
            convert_youtube(target_str, output_dir)
            return

        if "qiita.com" in domain:
            logger.info("Detected Qiita URL. Processing...")
            convert_qiita(target_str, output_dir)
            return

        if "zenn.dev" in domain:
            logger.info("Detected Zenn URL. Processing...")
            convert_zenn(target_str, output_dir)
            return

        if "wikipedia.org" in domain:
            logger.info("Detected Wikipedia URL. Processing...")
            convert_wikipedia(target_str, output_dir)
            return

        if "kokusho.nijl.ac.jp" in domain:
            logger.info("Detected Kokusho Database URL. Processing...")
            convert_kokusho(target_str, output_dir)
            return

        logger.info("Falling back to general website extraction...")
        convert_general_website(target_str, output_dir)

    except Exception as e:
        logger.error(f"Failed to process target '{target_str}': {e}", exc_info=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Web to Markdown Toolkit")
    parser.add_argument("target", help="URL, local file path, or directory path to convert")
    parser.add_argument(
        "--output-dir", type=Path, help="Optional output directory. Overrides CONVMD_OUTPUT_DIR."
    )
    parser.add_argument(
        "--transform",
        type=str,
        help="Optional instruction to transform the extracted Markdown file(s) using Gemini API (e.g., '現代語訳してください', '要約してください').",
    )
    parser.add_argument(
        "--obsidian-vault",
        type=Path,
        help="Path to your Obsidian vault. Output will be saved directly into this vault.",
    )
    parser.add_argument(
        "--open-obsidian",
        action="store_true",
        help="Automatically open the Obsidian app after conversion.",
    )
    parser.add_argument(
        "--notebooklm",
        type=str,
        help="NotebookLM Notebook ID to automatically upload the generated Markdown file(s).",
    )
    parser.add_argument(
        "--auto-link",
        action="store_true",
        help="Automatically extract keywords and convert them to Obsidian internal links ([[ ]]) and tags using AI.",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=0,
        help="Depth to crawl internal links when providing a URL (e.g., --depth 1). Default is 0 (single page).",
    )

    parser.add_argument(
        "--summary",
        action="store_true",
        help="Generate an Executive Summary across all processed files.",
    )
    parser.add_argument(
        "--slack-webhook",
        type=str,
        help="Slack Webhook URL to automatically send the generated Executive Summary.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=0,
        help="Run in daemon mode, repeating the process every N minutes.",
    )

    args = parser.parse_args()
    target_str = args.target

    # Determine output directory
    if args.obsidian_vault:
        output_dir = args.obsidian_vault.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
    elif args.output_dir:
        output_dir = args.output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = get_output_dir()

    logger.info(f"Output directory set to: {output_dir}")

    target_path = Path(target_str)

    def run_pipeline() -> None:
        # Record start time to find newly created files later
        start_time = time.time()

        # Phase 1: Parse & Extract
        if target_path.exists() and target_path.is_dir():
            logger.info(f"Detected directory input. Processing files recursively in: {target_path}")
            # Process files within the directory
            for file_path in target_path.rglob("*"):
                if file_path.is_file():
                    # Skip hidden files or system folders
                    if any(part.startswith(".") for part in file_path.parts):
                        continue
                    process_target(str(file_path), file_path, output_dir)
        else:
            # Process URL or File
            if not (target_path.exists() and target_path.is_file()) and args.depth > 0:
                logger.info(
                    f"Depth > 0 specified. Crawling URLs from {target_str} up to depth {args.depth}..."
                )
                from convmd.core.crawler import crawl_urls

                crawled_urls = crawl_urls(target_str, args.depth)
                for url in crawled_urls:
                    process_target(url, Path(url), output_dir)
            else:
                process_target(target_str, target_path, output_dir)

        # Phase 2: Post-processing Pipeline

        # Find files created or modified during this run
        new_md_files: List[Path] = []
        for md_file in output_dir.rglob("*.md"):
            if md_file.is_file() and md_file.stat().st_mtime >= start_time:
                # We filter out files that are already _transformed if they just got generated
                # to prevent double processing in edge cases, though start_time logic usually handles this.
                if (
                    not md_file.name.endswith("_transformed.md")
                    and not md_file.name.endswith("_linked.md")
                    and md_file.name != "executive_summary.md"
                ):
                    new_md_files.append(md_file)

        logger.info(
            f"Found {len(new_md_files)} newly generated markdown files for pipeline processing."
        )

        # 2.1 Transform (ユースケースA)
        from convmd.core.transform import (
            apply_obsidian_links,
            generate_executive_summary,
        )

        final_files_to_upload = list(new_md_files)
        if args.transform:
            final_files_to_upload = []
            for md_file in new_md_files:
                transformed_path = transform_markdown_with_gemini(md_file, args.transform)
                if transformed_path:
                    final_files_to_upload.append(transformed_path)
                else:
                    # Fallback to original if transform fails
                    final_files_to_upload.append(md_file)

        # 2.1.5 Auto-Linking
        if args.auto_link:
            linked_files = []
            for md_file in final_files_to_upload:
                linked_path = apply_obsidian_links(md_file)
                if linked_path:
                    linked_files.append(linked_path)
                else:
                    linked_files.append(md_file)
            final_files_to_upload = linked_files

        # 2.1.8 Summary & Slack Integration
        summary_path = None
        if args.summary and final_files_to_upload:
            combined_text = ""
            for md_file in final_files_to_upload:
                combined_text += f"\n\n--- Source: {md_file.name} ---\n\n"
                combined_text += md_file.read_text(encoding="utf-8")

            summary_path = generate_executive_summary(combined_text, output_dir)
            if summary_path:
                final_files_to_upload.append(summary_path)

        if args.slack_webhook and summary_path and summary_path.exists():
            from convmd.integrations.slack import send_to_slack

            summary_text = summary_path.read_text(encoding="utf-8")
            send_to_slack(args.slack_webhook, summary_text)

        # 2.2 NotebookLM (ユースケースB)
        if args.notebooklm:
            for md_file in final_files_to_upload:
                upload_to_notebooklm(args.notebooklm, md_file)

        # 2.3 Obsidian
        if args.open_obsidian:
            if args.obsidian_vault:
                open_in_obsidian(args.obsidian_vault)
            else:
                logger.warning(
                    "To use --open-obsidian, please provide the path to your vault with --obsidian-vault."
                )

    if args.interval > 0:
        logger.info(f"Starting daemon mode. Running pipeline every {args.interval} minutes.")
        try:
            while True:
                run_pipeline()
                logger.info(f"Sleeping for {args.interval} minutes...")
                time.sleep(args.interval * 60)
        except KeyboardInterrupt:
            logger.info("Daemon mode stopped by user.")
    else:
        run_pipeline()


if __name__ == "__main__":
    main()
