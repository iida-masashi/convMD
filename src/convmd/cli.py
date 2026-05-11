import argparse
import logging
from pathlib import Path
from urllib.parse import urlparse

from convmd.config import get_output_dir
from convmd.parsers.general import convert_general_website
from convmd.parsers.media.audio import convert_audio_file
from convmd.parsers.media.qiita import convert_qiita
from convmd.parsers.media.wikipedia import convert_wikipedia
from convmd.parsers.media.zenn import convert_zenn
from convmd.parsers.media.kokusho import convert_kokusho
from convmd.parsers.office import convert_office_file
from convmd.parsers.sns.note import convert_note_com
from convmd.parsers.sns.twitter import convert_twitter
from convmd.parsers.sns.youtube import convert_youtube

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

def main() -> None:
    parser = argparse.ArgumentParser(description="Web to Markdown Toolkit")
    parser.add_argument("target", help="URL or local file path to convert")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional output directory. Overrides CONVMD_OUTPUT_DIR."
    )
    parser.add_argument(
        "--transform",
        type=str,
        help="Optional instruction to transform a local Markdown file using Gemini API (e.g., '現代語訳してください', '要約してください')."
    )

    args = parser.parse_args()
    target_str = args.target

    # Determine output directory
    if args.output_dir:
        output_dir = args.output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = get_output_dir()

    logger.info(f"Output directory set to: {output_dir}")

    target_path = Path(target_str)

    # Check if target is a local file
    if target_path.exists() and target_path.is_file():
        logger.info(f"Detected local file: {target_path}")

        # Route to audio transcriber if it's an audio/video file
        audio_extensions = {".mp3", ".wav", ".m4a", ".mp4", ".flac", ".ogg", ".aac"}
        if target_path.suffix.lower() in audio_extensions:
            convert_audio_file(target_path, output_dir)
            return

        if target_path.suffix.lower() == ".md" and args.transform:
            from convmd.core.transform import transform_markdown_with_gemini
            transform_markdown_with_gemini(target_path, args.transform)
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

if __name__ == "__main__":
    main()
