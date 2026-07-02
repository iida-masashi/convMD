"""One-off: fetch a MediaWiki/Wikisource page to Markdown with a policy-compliant UA.

convMD's general parser sends the default ``Mozilla/5.0`` UA, which Wikimedia
rejects with 403. The dedicated wikipedia parser sends a compliant UA but its
URL parsing is hardwired to ``.wikipedia.org``. This script reuses convMD's own
pieces (get_html with a compliant UA, generate_frontmatter) plus a Wikisource-
aware HTML clean, then writes straight to the output dir — so the ``.convmd.yaml``
``obsidian_vault`` override can't redirect it.

Not part of the package (lives in scripts/, like the other one-off fetchers).

Usage:
    python scripts/wikisource_to_md.py <url> <output.md>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bs4 import BeautifulSoup  # noqa: E402
from markdownify import markdownify as md  # noqa: E402

from convmd.core.http import get_html  # noqa: E402
from convmd.core.utils import generate_frontmatter  # noqa: E402

# https://meta.wikimedia.org/wiki/User-Agent_policy — bare Mozilla/5.0 is 403'd.
_UA = {"User-Agent": "convmd/0.1 (+https://github.com/iida-masashi/convMD)"}


def _extract_body(html: str) -> tuple[str, str]:
    """Return (display_title, cleaned content HTML) from a MediaWiki page."""
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.select_one("#firstHeading") or soup.select_one("h1")
    display_title = title_tag.get_text(strip=True) if title_tag else "Untitled"

    content = soup.select_one("#mw-content-text") or soup
    # Strip MediaWiki UI chrome that markdownify would otherwise carry over.
    for sel in (
        ".mw-editsection",
        ".reference",
        ".navbox",
        ".metadata",
        ".catlinks",
        ".printfooter",
        ".mw-jump-link",
        ".noprint",
        "#toc",
        ".toc",
        "table.ws-noexport",
        "style",
        "script",
    ):
        for tag in content.select(sel):
            tag.decompose()
    return display_title, str(content)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url", help="Wikisource/MediaWiki page URL")
    ap.add_argument("out", help="output .md path")
    args = ap.parse_args()

    html = get_html(args.url, headers=_UA)
    if not html:
        print(f"ERROR: failed to fetch {args.url}", file=sys.stderr)
        return 2

    display_title, content_html = _extract_body(html)
    body = md(content_html, heading_style="ATX", escape_asterisks=False, escape_underscores=False)

    frontmatter = generate_frontmatter(display_title, args.url, tags=["wikisource", "ja"])

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(frontmatter + body, encoding="utf-8")
    print(f"WROTE {out_path} ({out_path.stat().st_size} bytes)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
