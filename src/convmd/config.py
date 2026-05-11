import os
from pathlib import Path
from typing import Final

# Default output directory is 'output' in the current working directory
_DEFAULT_OUTPUT_DIR: Final[str] = str(Path.cwd() / "output")

# Fetch from environment variable or use default
OUTPUT_DIR_STR: Final[str] = os.environ.get("CONVMD_OUTPUT_DIR", _DEFAULT_OUTPUT_DIR)
OUTPUT_DIR: Final[Path] = Path(OUTPUT_DIR_STR).resolve()

def get_output_dir() -> Path:
    """Returns the configured output directory, creating it if it doesn't exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR
