"""One-off: OCR a (scanned, no-text-layer) PDF to Markdown via Gemini, page by page.

convMD's office/PDF route uses MarkItDown, which returns empty text for scanned
PDFs (no text layer). A single whole-PDF Gemini call dropped a page even at
finish_reason=STOP, so this splits the PDF into single pages (pypdf) and OCRs
each page independently — guaranteeing per-page coverage — then assembles one MD
with an ai_ocr evidence callout. Each page's output is small, so truncation is a
non-issue; the per-page finish_reason is still checked.

Not part of the package (lives in scripts/, like the other one-off crawlers).

Usage:
    python scripts/pdf_ocr_to_md.py <pdf_url_or_path> <output.md> [--source-url URL]
"""

from __future__ import annotations

import argparse
import datetime
import io
import sys
import urllib.request
from pathlib import Path

# Make the package importable when run as a standalone script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from convmd.constants import Models  # noqa: E402
from convmd.core.gemini import get_client, strip_code_fence, usage_tracker  # noqa: E402

VERBATIM_PROMPT = (
    "You are an OCR transcription engine. This image is ONE page (which may be a "
    "two-page spread) of a scanned academic paper. Transcribe ALL text into clean "
    "Markdown, in reading order (for a spread: left column/page fully, then right).\n"
    "STRICT RULES:\n"
    "- Transcribe VERBATIM. Do NOT summarize, paraphrase, translate, or omit anything.\n"
    "- Do NOT invent, complete, or 'fix' headings, author names, dates, citations, or "
    "footnotes. If text is illegible, write [illegible] rather than guessing.\n"
    "- Preserve footnotes/endnotes exactly, with their numbering.\n"
    "- Keep Chinese characters / proper nouns exactly as printed.\n"
    "- Render tables as Markdown tables only if clearly tabular; otherwise keep raw lines.\n"
    "Output ONLY the transcription, no preamble, no page markers."
)


def _load_env_key() -> None:
    """Set GEMINI/GOOGLE_API_KEY into os.environ from .env without printing it."""
    import os

    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return
    here = Path(__file__).resolve()
    candidates = [here.parents[1] / ".env", here.parents[2] / ".env"]
    env_path = next((c for c in candidates if c.exists()), None)
    if env_path is None:
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, val = line.partition("=")
        name = name.strip()
        val = val.strip().strip('"').strip("'")
        if name in ("GEMINI_API_KEY", "GOOGLE_API_KEY") and val:
            os.environ[name] = val


def _read_pdf_bytes(target: str) -> bytes:
    if target.startswith(("http://", "https://")):
        req = urllib.request.Request(target, headers={"User-Agent": "Mozilla/5.0"})
        return urllib.request.urlopen(req, timeout=180).read()
    return Path(target).read_bytes()


def _split_pages(pdf_bytes: bytes) -> list[bytes]:
    """Return a single-page PDF (as bytes) for each page in the source."""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(io.BytesIO(pdf_bytes))
    out: list[bytes] = []
    for page in reader.pages:
        w = PdfWriter()
        w.add_page(page)
        buf = io.BytesIO()
        w.write(buf)
        out.append(buf.getvalue())
    return out


def _ocr_page(client, model: str, page_bytes: bytes):
    """OCR one single-page PDF. Returns (text, finish_reason, raw_response).

    Per-call timeout (300s) + one retry so a stalled call errors and re-runs
    instead of hanging the whole batch. Usage is recorded by the caller after
    the join to avoid racing the shared tracker across threads.
    """
    from google.genai import types

    part = types.Part.from_bytes(data=page_bytes, mime_type="application/pdf")
    config = types.GenerateContentConfig(
        max_output_tokens=65536,
        http_options=types.HttpOptions(timeout=300_000),  # ms
    )
    last_exc: Exception | None = None
    for _ in range(2):
        try:
            response = client.models.generate_content(
                model=model, contents=[VERBATIM_PROMPT, part], config=config
            )
            finish = None
            try:
                finish = str(response.candidates[0].finish_reason)
            except Exception:
                pass
            return strip_code_fence(response.text or ""), finish, response
        except Exception as e:
            last_exc = e
    raise last_exc  # type: ignore[misc]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="PDF URL or local path")
    ap.add_argument("out", help="output .md path")
    ap.add_argument("--source-url", default=None, help="canonical source URL for frontmatter")
    ap.add_argument("--model", default=Models.GEMINI_PRO)
    args = ap.parse_args()

    _load_env_key()
    client = get_client()
    if client is None:
        print("ERROR: no Gemini API key (GEMINI_API_KEY/GOOGLE_API_KEY).", file=sys.stderr)
        return 2

    pdf_bytes = _read_pdf_bytes(args.target)
    pages = _split_pages(pdf_bytes)
    n = len(pages)
    print(f"PDF: {len(pdf_bytes)} bytes, {n} pages; OCR via {args.model} (parallel)...",
          file=sys.stderr)

    from concurrent.futures import ThreadPoolExecutor

    # Pages are independent — run concurrently. Reassemble by index (NOT
    # completion order) so a citation source can never be silently reordered.
    results: dict[int, tuple[str, str | None, object]] = {}

    def work(i: int):
        return i, _ocr_page(client, args.model, pages[i - 1])

    with ThreadPoolExecutor(max_workers=4) as ex:
        future_to_idx = {ex.submit(work, i): i for i in range(1, n + 1)}
        for fut, idx in future_to_idx.items():
            try:
                i, (text, finish, resp) = fut.result()
                results[i] = (text, finish, resp)
            except Exception as e:  # noqa: BLE001
                print(f"  page {idx}: exception {type(e).__name__}: {e}", file=sys.stderr)

    # Record usage once, on the main thread, after the join.
    for _i, (_t, _f, resp) in results.items():
        usage_tracker().record(args.model, resp)

    failures: list[int] = []
    for i in range(1, n + 1):
        if i not in results:
            print(f"  page {i}/{n}: FAILED (exception)", file=sys.stderr)
            failures.append(i)
            continue
        text, finish, _ = results[i]
        ok = bool(text.strip()) and (finish is None or "STOP" in finish.upper())
        print(f"  page {i}/{n}: chars={len(text.strip())} finish={finish} ok={ok}",
              file=sys.stderr)
        if not ok:
            failures.append(i)

    if failures:
        print(f"ERROR: pages with empty/truncated/failed OCR: {failures}. NOT writing.",
              file=sys.stderr)
        return 4

    sections = [f"<!-- page {i} -->\n\n{results[i][0].strip()}" for i in range(1, n + 1)]

    body = "\n\n---\n\n".join(sections)
    source = args.source_url or args.target
    created = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    frontmatter = (
        "---\n"
        f'title: "{Path(args.out).stem}"\n'
        f'source: "{source}"\n'
        f'created_at: "{created}"\n'
        f'model: "{args.model}"\n'
        f"pages: {len(pages)}\n"
        "evidence_type: ai_ocr\n"
        "tags:\n"
        '  - "pdf"\n'
        '  - "ai_ocr"\n'
        "---\n\n"
        "> [!warning] AI-OCR — 要原典照合\n"
        "> このノートはスキャン画像PDFをGeminiでページ単位にOCRしたものです。LLM-OCRは"
        "誤読・脱字・補完のリスクがあります。引用前に必ず原典PDFと照合してください。\n"
        f"> 原典: {source}\n\n"
    )
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(frontmatter + body + "\n", encoding="utf-8")

    u = usage_tracker().by_model.get(args.model)
    if u:
        print(f"tokens in={u.input_tokens} out={u.output_tokens} calls={u.calls}", file=sys.stderr)
    print(f"WROTE {out_path} ({out_path.stat().st_size} bytes, {len(pages)} pages)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
