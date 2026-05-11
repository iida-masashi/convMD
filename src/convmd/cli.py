import argparse
import logging
from pathlib import Path

from convmd.config import get_output_dir
from convmd.parsers.general import convert_general_website
from convmd.parsers.office import convert_office_file

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
        convert_office_file(target_path, output_dir)
        return

    # Treat as URL
    logger.info(f"Analyzing URL: {target_str}")
    convert_general_website(target_str, output_dir)

if __name__ == "__main__":
    main()
