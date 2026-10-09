"""Centralized dispatch from a URL to the appropriate parser.

Each route is a ``(predicate, handler)`` pair. The first match wins.

Handlers re-resolve their target function from its module at call time (rather than
binding it at registration time). This keeps patches like
``patch("convmd.parsers.sns.youtube.convert_youtube")`` effective in tests.
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any, Callable, cast
from urllib.parse import ParseResult, urlparse

from convmd.cli_args import RunConfig

logger = logging.getLogger(__name__)

Predicate = Callable[[ParseResult], bool]
Handler = Callable[[str, ParseResult, Path, RunConfig], Path | None]

# Module-scope so dispatch_url can also consult it to keep binary URLs out of
# the text-decoding LLM fallback paths.
_OFFICE_SUFFIXES: tuple[str, ...] = (".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls")


def _is_binary_url(target_url: str) -> bool:
    """True iff the URL path ends in a known binary office/PDF suffix.

    ``get_html`` would force-decode such bodies as text (mojibake), so the
    ``--ai-extract`` shortcut and semantic-fallback branches must skip them
    and let the office route handle the download.
    """
    return urlparse(target_url).path.lower().endswith(_OFFICE_SUFFIXES)


def _is_edinet_target(target_url: str) -> bool:
    """``edinet:<code>`` is an API target, not a web page; HTML/LLM fallbacks don't apply."""
    return urlparse(target_url).scheme == "edinet"


# A result whose body (frontmatter excluded) is shorter than this is treated as a failed
# extraction and retried with AI. Counting raw file bytes let a frontmatter-only file
# with a long title/URL pass as a success.
_MIN_BODY_CHARS = 100


def _is_too_small(path: Path) -> bool:
    from convmd.core.utils import body_text

    try:
        return len(body_text(path.read_text(encoding="utf-8", errors="ignore"))) < _MIN_BODY_CHARS
    except OSError:
        return True


def _has_domain(*needles: str) -> Predicate:
    def check(p: ParseResult) -> bool:
        return any(n in p.netloc for n in needles)

    return check


def _dynamic_call(module: str, func: str, *args: Any, **kwargs: Any) -> Any:
    mod = importlib.import_module(module)
    fn = getattr(mod, func)
    return fn(*args, **kwargs)


def _route(predicate: Predicate, module: str, func: str, log_message: str | None = None,
           pass_cfg_kwargs: tuple[str, ...] = ()) -> tuple[Predicate, Handler]:
    """Build a route that dynamically resolves ``module.func`` at dispatch time."""

    def handler(url: str, _p: ParseResult, out: Path, cfg: RunConfig) -> Path | None:
        if log_message:
            logger.info(log_message)
        kwargs = {k: getattr(cfg, k) for k in pass_cfg_kwargs}
        return cast("Path | None", _dynamic_call(module, func, url, out, **kwargs))

    return predicate, handler


def _route_note(predicate: Predicate) -> tuple[Predicate, Handler]:
    def handler(url: str, p: ParseResult, out: Path, _cfg: RunConfig) -> Path | None:
        parts = p.path.strip("/").split("/")
        if len(parts) == 1:
            logger.info("Detected note.com creator profile. Fetching all notes...")
            return cast(
                "Path | None",
                _dynamic_call("convmd.parsers.sns.note", "convert_note_com", parts[0], out),
            )
        else:
            return cast(
                "Path | None",
                _dynamic_call("convmd.parsers.general", "convert_general_website", url, out),
            )

    return predicate, handler


def _route_twitter(predicate: Predicate) -> tuple[Predicate, Handler]:
    def handler(url: str, p: ParseResult, out: Path, _cfg: RunConfig) -> Path | None:
        parts = p.path.strip("/").split("/")
        if parts:
            screen_name = parts[0]
            logger.info(f"Detected X.com account: @{screen_name}. Fetching recent posts via Grok...")
            return cast(
                "Path | None",
                _dynamic_call("convmd.parsers.sns.grok", "convert_grok", screen_name, out),
            )
        return None

    return predicate, handler


def _build_routes() -> list[tuple[Predicate, Handler]]:
    routes: list[tuple[Predicate, Handler]] = [
        _route(
            lambda p: p.scheme == "edinet",
            "convmd.parsers.media.edinet",
            "convert_edinet",
            "Detected EDINET target. Fetching XBRL CSV via EDINET API...",
            pass_cfg_kwargs=("edinet_days",),
        ),
        _route_note(_has_domain("note.com")),
        _route_twitter(_has_domain("x.com", "twitter.com")),
        _route(
            _has_domain("youtube.com", "youtu.be"),
            "convmd.parsers.sns.youtube",
            "convert_youtube",
            "Detected YouTube video. Extracting transcript...",
        ),
        _route(
            _has_domain("qiita.com"),
            "convmd.parsers.media.qiita",
            "convert_qiita",
            "Detected Qiita URL. Processing...",
        ),
        _route(
            _has_domain("zenn.dev"),
            "convmd.parsers.media.zenn",
            "convert_zenn",
            "Detected Zenn URL. Processing...",
        ),
        _route(
            _has_domain("wikipedia.org"),
            "convmd.parsers.media.wikipedia",
            "convert_wikipedia",
            "Detected Wikipedia URL. Processing...",
        ),
        _route(
            _has_domain("kokusho.nijl.ac.jp"),
            "convmd.parsers.media.kokusho",
            "convert_kokusho",
            "Detected Kokusho Database URL. Processing...",
            pass_cfg_kwargs=("bilingual", "ocr"),
        ),
        _route(
            _has_domain("digital.archives.go.jp"),
            "convmd.parsers.media.naj",
            "convert_naj",
            "Detected National Archives of Japan URL. Processing...",
            pass_cfg_kwargs=("ocr",),
        ),
        _route(
            _has_domain("dl.ndl.go.jp"),
            "convmd.parsers.media.ndl",
            "convert_ndl",
            "Detected NDL Digital Collection URL. Processing...",
            pass_cfg_kwargs=("ocr",),
        ),
        _route(
            _has_domain("github.com"),
            "convmd.parsers.sns.github",
            "convert_github",
            "Detected GitHub URL. Processing...",
        ),
        _route(
            _has_domain("reddit.com"),
            "convmd.parsers.sns.reddit",
            "convert_reddit",
            "Detected Reddit URL. Processing...",
        ),
        _route(
            _has_domain("news.ycombinator.com"),
            "convmd.parsers.sns.hackernews",
            "convert_hackernews",
            "Detected Hacker News item. Processing...",
        ),
        _route(
            _has_domain("hatenablog.com", "b.hatena.ne.jp", "hatenablog.jp"),
            "convmd.parsers.media.hatena",
            "convert_hatena",
            "Detected Hatena URL. Processing...",
        ),
        _route(
            _has_domain("substack.com"),
            "convmd.parsers.media.substack",
            "convert_substack",
            "Detected Substack URL. Processing...",
        ),
        _route(
            _has_domain("medium.com"),
            "convmd.parsers.media.medium",
            "convert_medium",
            "Detected Medium URL. Processing...",
        ),
        _route(
            _has_domain("speakerdeck.com"),
            "convmd.parsers.media.speakerdeck",
            "convert_speakerdeck",
            "Detected SpeakerDeck URL. Processing...",
        ),
    ]

    def is_rss(p: ParseResult) -> bool:
        return p.path.endswith((".rss", ".xml", "/feed", "/rss"))

    def podcast_handler(url: str, _p: ParseResult, out: Path, cfg: RunConfig) -> Path | None:
        logger.info("Detected RSS feed. Treating as podcast...")
        _dynamic_call(
            "convmd.parsers.media.podcast",
            "convert_podcast",
            url,
            out,
            limit=cfg.podcast_limit,
        )
        return None

    routes.append((is_rss, podcast_handler))

    def is_office_url(p: ParseResult) -> bool:
        return p.path.lower().endswith(_OFFICE_SUFFIXES)

    def office_url_handler(url: str, p: ParseResult, out: Path, cfg: RunConfig) -> Path | None:
        import tempfile
        import urllib.parse
        from pathlib import Path as _P

        from convmd.core.http import download_binary
        from convmd.parsers.office import convert_office_file

        suffix = _P(p.path).suffix.lower()
        filename = _P(urllib.parse.unquote(p.path)).name or f"download{suffix}"
        logger.info(f"Detected {suffix.upper()} URL. Downloading and processing via markitdown...")
        with tempfile.TemporaryDirectory() as td:
            local = _P(td) / filename
            if not download_binary(url, local):
                logger.error(f"Failed to download {url}")
                return None
            return convert_office_file(
                local,
                out,
                ai_extract=cfg.ai_extract if cfg else False,
                schema=cfg.schema if cfg else None,
            )

    routes.append((is_office_url, office_url_handler))

    def fallback_handler(url: str, _p: ParseResult, out: Path, _cfg: RunConfig) -> Path | None:
        logger.info("Falling back to general website extraction...")
        return cast(
            "Path | None",
            _dynamic_call("convmd.parsers.general", "convert_general_website", url, out),
        )

    routes.append((lambda _p: True, fallback_handler))
    return routes


_routes_cache: list[tuple[Predicate, Handler]] | None = None


def _routes() -> list[tuple[Predicate, Handler]]:
    global _routes_cache
    if _routes_cache is None:
        _routes_cache = _build_routes()
    return _routes_cache


def dispatch_url(target_url: str, output_dir: Path, cfg: RunConfig | None = None) -> None:
    """Dispatch a URL to the first matching parser."""
    if cfg is None:
        cfg = RunConfig(target=target_url, output_dir=output_dir)

    # Force AI extract if requested — but skip for binary office/PDF URLs,
    # where get_html would force-decode the body as text and feed garbage to
    # the LLM. Those fall through to the office route, which downloads via
    # download_binary and runs markitdown (which itself honors ai_extract).
    if cfg.ai_extract and not _is_binary_url(target_url) and not _is_edinet_target(target_url):
        from convmd.core.http import get_html
        from convmd.core.llm_extractor import extract_with_llm

        html = get_html(target_url)
        if html:
            extract_with_llm(html, output_dir, url=target_url, schema=cfg.schema)
            return

    parsed = urlparse(target_url)
    is_binary = _is_binary_url(target_url) or _is_edinet_target(target_url)
    for predicate, handler in _routes():
        if predicate(parsed):
            try:
                res_path = handler(target_url, parsed, output_dir, cfg)

                # Semantic Fallback: if result is missing or too small, try AI.
                # Skip for binary URLs — get_html would decode bytes as text.
                if not is_binary and (
                    not res_path
                    or (res_path.exists() and _is_too_small(res_path))
                ):
                    logger.info(f"Extraction result for {target_url} was empty or too small. Trying AI...")
                    from convmd.core.http import get_html
                    from convmd.core.llm_extractor import extract_with_llm

                    html = get_html(target_url, render_js=getattr(cfg, "render_js", False))
                    if html:
                        extract_with_llm(html, output_dir, url=target_url, schema=getattr(cfg, "schema", None))

            except Exception:
                logger.exception(f"Handler failed for {target_url}")
                if is_binary:
                    # Same reason: don't feed decoded binary to the LLM.
                    return
                # Fallback to AI extraction on failure
                from convmd.core.http import get_html
                from convmd.core.llm_extractor import extract_with_llm

                html = get_html(target_url, render_js=getattr(cfg, "render_js", False))
                if html:
                    logger.info(f"Retrying {target_url} with AI autonomous extraction...")
                    extract_with_llm(html, output_dir, url=target_url, schema=getattr(cfg, "schema", None))
            return
    logger.error(f"No route matched for {target_url}")
