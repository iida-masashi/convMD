"""Thin subprocess wrapper around ``browser4-cli`` (https://github.com/platonai/Browser4).

Used only as a fallback when Playwright rendering fails or is unavailable — see
``core.http.get_html_with_js``. Not a general-purpose Browser4 client.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

_PAGE_URL_RE = re.compile(r"^- Page URL: (.+)$", re.MULTILINE)


def _executable() -> str | None:
    """Resolve the full path to the browser4-cli executable.

    On Windows, ``shutil.which`` resolves the ``.CMD`` shim via PATHEXT, but
    ``subprocess.run(["browser4-cli", ...])`` does not reliably do the same
    resolution itself — pass the resolved path explicitly.
    """
    return shutil.which("browser4-cli")


def is_available() -> bool:
    """True iff the ``browser4-cli`` binary is on PATH."""
    return _executable() is not None


def get_html_with_browser4(url: str, timeout: float) -> str | None:
    """Render ``url`` in a real Chrome via browser4-cli and return the HTML, or None on failure.

    Runs each call in its own session (random name) and temp working directory so
    concurrent/batch invocations don't share or race on ``.browser4-cli/`` state.
    The session is always closed afterward to release the browser process.
    """
    exe = _executable()
    if exe is None:
        return None

    session = f"convmd-{uuid.uuid4().hex[:8]}"
    timeout_s = int(timeout)

    with tempfile.TemporaryDirectory(prefix="convmd_browser4_") as tmpdir:
        cwd = Path(tmpdir)
        html_path = cwd / "snapshot.html"

        try:
            goto = subprocess.run(
                [exe, "-s", session, "goto", url],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
            if goto.returncode != 0:
                logger.error(f"browser4-cli goto failed for {url}: {goto.stderr.strip()}")
                return None

            match = _PAGE_URL_RE.search(goto.stdout)
            if match and match.group(1).strip().startswith("chrome-error://"):
                logger.error(f"browser4-cli could not load {url} (chrome-error page)")
                return None

            capture = subprocess.run(
                [exe, "-s", session, "htmlsnapshot", "capture"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
            if capture.returncode != 0:
                logger.error(
                    f"browser4-cli htmlsnapshot capture failed for {url}: {capture.stderr.strip()}"
                )
                return None

            export = subprocess.run(
                [exe, "-s", session, "htmlsnapshot", "export", "--file", str(html_path)],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
            if export.returncode != 0 or not html_path.exists():
                logger.error(
                    f"browser4-cli htmlsnapshot export failed for {url}: {export.stderr.strip()}"
                )
                return None

            return html_path.read_text(encoding="utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            logger.error(f"browser4-cli timed out for {url}")
            return None
        except Exception as e:
            logger.error(f"browser4-cli failed for {url}: {e}")
            return None
        finally:
            subprocess.run(
                [exe, "-s", session, "close"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
