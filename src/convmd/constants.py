"""Centralized constants — single source of truth for suffixes, model names, and HTTP defaults."""

from typing import Final


class Suffix:
    TRANSFORMED: Final[str] = "_transformed.md"
    LINKED: Final[str] = "_linked.md"
    DIFF: Final[str] = "_diff.md"
    SUMMARY: Final[str] = "executive_summary.md"


class Models:
    GEMINI_PRO: Final[str] = "gemini-3.1-pro-preview"
    GEMINI_FLASH: Final[str] = "gemini-3-flash-preview"


USER_AGENT: Final[str] = "Mozilla/5.0"
DEFAULT_TIMEOUT: Final[float] = 60.0
DOWNLOAD_TIMEOUT: Final[float] = 60.0
CRAWL_TIMEOUT: Final[float] = 60.0
