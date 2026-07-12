"""``convmd doctor`` — environment health checks and a diagnostic report.

Prints one line per check, prefixed with an ASCII status tag ([OK]/[WARN]/[FAIL]/[MISSING])
instead of emoji, since emoji can break some Windows terminals. This is a diagnostic tool,
not a gate: it never exits non-zero.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sys
from pathlib import Path

from convmd.config_file import load_config
from convmd.core.gemini import is_configured

# Maps the module name importlib checks against to the `uv sync --extra <name>` hint,
# per pyproject.toml [project.optional-dependencies] (group name, not the PyPI package name).
_OPTIONAL_EXTRAS = [
    ("faster_whisper", "whisper", "audio transcription"),
    ("playwright", "render", "JavaScript rendering (--render-js)"),
    ("notebooklm_py", "notebooklm", "NotebookLM upload (--notebooklm)"),
    ("PIL", "image", "image handling"),
    ("yt_dlp", "scripts", "YouTube subtitle scripts"),
]


def _is_installed(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ValueError):
        return False


def _check_python_version() -> str:
    version = sys.version_info
    if version >= (3, 10):
        return f"[OK] Python version: {version.major}.{version.minor}.{version.micro} (>=3.10 required)"
    return f"[FAIL] Python version: {version.major}.{version.minor}.{version.micro} (>=3.10 required)"


def _check_pandoc() -> str:
    path = shutil.which("pandoc")
    if path:
        return f"[OK] pandoc found: {path}"
    return (
        "[MISSING] pandoc not found on PATH -- "
        "--format epub/pdf/docx/html will not work"
    )


def _check_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if path:
        return f"[OK] ffmpeg found: {path}"
    return (
        "[MISSING] ffmpeg not found on PATH -- "
        "audio transcription (faster-whisper) will not work"
    )


def _check_gemini_key() -> str:
    if is_configured():
        var = "GEMINI_API_KEY" if os.environ.get("GEMINI_API_KEY") else "GOOGLE_API_KEY"
        return f"[OK] Gemini API key found (via {var})"
    return (
        "[MISSING] GEMINI_API_KEY / GOOGLE_API_KEY not set -- "
        "AI features (--transform, --auto-link, --bilingual, --ai-extract, etc.) will not work"
    )


def _check_optional_extras() -> list[str]:
    lines = []
    for module_name, extra_name, purpose in _OPTIONAL_EXTRAS:
        if _is_installed(module_name):
            lines.append(f"[OK] {module_name} installed ({purpose})")
        else:
            lines.append(
                f"[MISSING] {module_name} not installed -- {purpose} unavailable "
                f"(uv sync --extra {extra_name})"
            )
    return lines


def _check_browser4_cli() -> str:
    path = shutil.which("browser4-cli")
    if path:
        return f"[OK] browser4-cli found: {path} (Playwright rendering fallback)"
    return (
        "[MISSING] browser4-cli not found on PATH -- "
        "unavailable as a --render-js fallback (npm install -g browser4-cli)"
    )


def _check_playwright_browsers() -> str | None:
    """If playwright is installed, check whether its browser binaries are present.

    Uses ``chromium.executable_path`` (a plain path lookup, no browser launch) rather than
    actually launching chromium, since launching is slower and can fail for unrelated
    reasons (sandboxing, missing OS deps) that aren't what this check is about.
    Returns None if playwright itself isn't installed (nothing to check).
    """
    if not _is_installed("playwright"):
        return None
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            if Path(p.chromium.executable_path).exists():
                return "[OK] playwright browser binaries found"
        return (
            "[WARN] playwright installed but browser binaries missing -- "
            "run: playwright install chromium"
        )
    except Exception as e:
        return f"[WARN] could not verify playwright browser binaries: {e}"


def _check_config_files() -> list[str]:
    lines = []
    home_path = Path.home() / ".convmd.yaml"
    cwd_path = Path.cwd() / ".convmd.yaml"

    for label, path in (("~/.convmd.yaml", home_path), ("./.convmd.yaml", cwd_path)):
        if path.is_file():
            lines.append(f"[OK] {label} found: {path}")
        else:
            lines.append(f"[MISSING] {label} not found")

    config = load_config()
    if config:
        keys = ", ".join(sorted(config.keys()))
        lines.append(f"[OK] merged config keys: {keys}")
        if config.get("obsidian_vault"):
            lines.append(
                "[WARN] obsidian_vault is set in config -- it takes precedence over "
                "--output-dir unless --output-dir is explicitly passed on the command line"
            )
    return lines


def _check_output_dir_env() -> str:
    value = os.environ.get("CONVMD_OUTPUT_DIR")
    if value:
        return f"[OK] CONVMD_OUTPUT_DIR set: {value}"
    return "[MISSING] CONVMD_OUTPUT_DIR not set -- default output dir is ./output"


def run_doctor(args: argparse.Namespace) -> None:
    lines = [
        _check_python_version(),
        _check_pandoc(),
        _check_ffmpeg(),
        _check_gemini_key(),
        *_check_optional_extras(),
    ]

    playwright_line = _check_playwright_browsers()
    if playwright_line:
        lines.append(playwright_line)

    lines.append(_check_browser4_cli())

    lines.extend(_check_config_files())
    lines.append(_check_output_dir_env())

    print("convmd doctor -- environment health check")
    print("=" * 42)
    for line in lines:
        print(line)
