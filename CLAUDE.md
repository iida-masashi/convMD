# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> General guidelines for this codebase: think before coding (state assumptions, surface tradeoffs instead of picking silently), keep changes minimal and surgical (touch only what the task requires, don't refactor unrelated code), and match existing style.

## What this is

convMD converts web sources (articles, SNS posts, video/audio, digital archives) and local Office/PDF files into Markdown for knowledge bases like Obsidian. A single CLI entry point dispatches each target URL/path to the right parser, then runs it through a post-processing pipeline. The user-facing feature list and examples are in `README.md` (Japanese) — read it for *what* the tool does; this file covers *how the code is wired*.

## Commands

Package manager is **uv**. The venv is `.venv/`.

```bash
uv sync --all-extras                 # install deps for development (incl. dev group + all optional extras)
uv run python -m convmd.cli <target> # run the CLI (URL, file, or dir)
uv run convmd <target>               # same via the installed entry point

uv run pytest                        # full test suite (requires --all-extras: some tests patch optional deps like faster-whisper)
uv run pytest tests/test_routing.py  # one file
uv run pytest tests/test_routing.py::test_name   # one test
uv run pytest -k "kokusho"           # by keyword

uv run ruff check .                  # lint
uv run ruff format .                 # format (line-length 100)
uv run mypy src                      # type check — must pass strict (disallow_untyped_defs)
```

mypy runs in strict mode and `tests/` is excluded from it. Every function in `src/` needs full type hints or mypy fails.

## Architecture

The flow is **CLI → routing → parser → pipeline phases**. Three modules carry the structure:

- **`cli.py`** — thin entry point. Detects the `find` subcommand by sniffing `sys.argv[1]` before argparse (there are no real subparsers — the `convmd <target>` shape is preserved verbatim). Does a two-pass parse so YAML config can set argparse defaults before the real parse.
- **`cli_args.py`** — `build_parser()` + the typed `RunConfig` dataclass. `RunConfig` is the single config object threaded through everything. `to_run_config` uses a tolerant `_typed()` getter so partially-stubbed test args don't break it.
- **`pipeline.py`** — `run_pipeline` → `run_once` runs phases in order: **extract → diff → transform → link → summary → dispatch**. Each phase takes the list of Markdown files from the previous one. `extract_phase` also rescans `output_dir` for files newer than `start_time` to catch multi-file outputs (crawling, image sets) that handlers don't return directly.
- **`routing.py`** — `dispatch_url` matches the URL against an ordered `(predicate, handler)` list; **first match wins**, with a catch-all fallback to general extraction. Add a new site by adding a route in `_build_routes()`.

### Routing conventions (important)

- Routes resolve their handler **dynamically at dispatch time** via `_dynamic_call(module, func, ...)` (importlib + getattr), *not* by binding the function at registration. This is deliberate: it keeps `patch("convmd.parsers.sns.youtube.convert_youtube")` and similar test patches effective. Follow this pattern when adding routes — don't import parser functions at module top level into the route table.
- A handler's standard signature is `(url, output_dir, **cfg_kwargs) -> Path | None`. Pass selected `RunConfig` fields through with `pass_cfg_kwargs=(...)` (see the kokusho/naj/ndl routes passing `ocr`/`bilingual`).
- `dispatch_url` has **two AI fallbacks**: if a handler raises, or if its output body (frontmatter excluded) is under `_MIN_BODY_CHARS` (100) chars, it retries with `extract_with_llm` (Gemini autonomous DOM extraction). `--ai-extract` forces this path up front.
- Output safety: parsers that write via `core/utils.unique_output_path` (general, AI extract) never overwrite a file from a *different* `source:` — they append `_2`, `_3`, …; the same source is overwritten in place. AI extracts get `extraction: ai` frontmatter, and numbers (≥3 digits) not found in the source are listed in `unverified_numbers` with a CAUTION callout. `run_pipeline` returns False (CLI exits 1) when a single target produced no Markdown or a batch left failed targets.

### Parser contract

Each parser module exposes a `convert_<site>(url, output_dir, ...) -> Path | None` function that writes one or more `.md` files into `output_dir` and returns the primary path (or `None` for multi-file outputs). Parsers live in `parsers/media/` (publishing platforms, archives, audio) and `parsers/sns/` (social). Standard helpers:

- `core/http.py` — **all** HTTP goes through here (`get_html`, `get_json`, `download_binary`). It centralizes the httpx client, `USER_AGENT`, timeouts, and TLS config. TLS verification is on by default; `CONVMD_INSECURE_SSL=1` disables it. Don't create httpx clients elsewhere.
- `core/utils.py` — `generate_frontmatter(title, url, tags=...)` and `sanitize_filename(...)`. Use these for consistent YAML frontmatter and safe filenames.
- `core/download.py` — `process_images(body, base_url, output_dir)` for inlined image handling.

### EDINET (`parsers/media/edinet.py`)

- Target scheme `edinet:<docID|secCode|EDINET code>` is routed first (`p.scheme == "edinet"`) and is excluded from the `--ai-extract` shortcut and the HTML/LLM fallbacks (`_is_edinet_target`), like binary URLs.
- Uses EDINET API v2 (spec: ESE140206.pdf): `documents.json?date=…&type=2` for daily lists, `documents/{docID}?type=5` for the XBRL_TO_CSV ZIP. Errors may arrive as HTTP 200 with a JSON body (`metadata.status` or `StatusCode`) — `_api_error` handles both. Company lookup walks daily lists back `edinet_days` (weekends skipped) because there is no per-company endpoint.
- The key goes in the `Subscription-Key` query param; `core/http.redact` plus a filter on the `httpx` logger mask it in every log line. Keep both if you touch HTTP logging.
- CSV is UTF-16 TSV; columns are read by Japanese header names (`要素ID`, `項目名`, `コンテキストID`, `相対年度`, `連結・個別`, `値` …) and a mismatched header raises instead of producing an empty table. Only whole-company contexts (`^[A-Za-z0-9]+(_NonConsolidatedMember)?$`) are rendered; TextBlocks and segment members are skipped, and the "other" section keeps numeric values only. Tables are keyed by (section, 連結・個別, 期間・時点); real filings can have `連結・個別` = `その他` for every row, so the scope heading is shown only when a section has more than one. Columns sort 当→前→前々 (`_year_rank`). Values are copied verbatim (thousands separators only).

### Gemini / cost

All Gemini calls go through `core/gemini.py`, which resolves the key (`GEMINI_API_KEY` or `GOOGLE_API_KEY`), builds the client, strips code fences, and records token usage in a `UsageTracker`. Model names are constants in `constants.py` (`Models.GEMINI_PRO` = `gemini-3.1-pro-preview`, `Models.GEMINI_FLASH` = `gemini-3.8-flash`). The cost table in `pipeline._PRICE_USD_PER_1M_TOKENS` is keyed by those model strings — update both together if a model changes.

### Cache & diff

`core/cache.py` backs a SQLite db (`.convmd.db`) at the output root, storing a content hash per source. `diff_phase` skips downstream work when the hash is unchanged; with `--diff-only` it writes a `*_diff.md` (unified diff). Pipeline artifacts are recognized by suffix via `constants.Suffix` (`_transformed.md`, `_linked.md`, `_diff.md`, `executive_summary.md`) and excluded from the "new files" rescan.

## Conventions

- **Single source of truth** for suffixes, model names, and HTTP defaults is `constants.py`. Don't hardcode these strings in parsers.
- New CLI flags: add to `build_parser()`, add the field to `RunConfig`, and wire it in `to_run_config` with `_typed(...)`. YAML config keys mirror flag names in snake_case (`--obsidian-vault` → `obsidian_vault`); config precedence is CLI > `--config <path>` > `./.convmd.yaml` > `~/.convmd.yaml`.
- `cli.py` re-exports `process_target`, `transform_markdown_with_gemini`, `upload_to_notebooklm` and keeps `argparse`/`time` importable at module level **for legacy test patch surfaces** — the `# noqa` comments mark these; don't remove them.
- Use `pathlib.Path` everywhere (cross-platform; primary dev is Windows/PowerShell). Default output is `./output/`, overridable via `--output-dir` or `CONVMD_OUTPUT_DIR`; `--obsidian-vault` overrides both.
- `scripts/` holds one-off standalone crawl/transcript scripts, not part of the package.

## Dependency constraints

- `firecrawl-anydoc` is pinned `<0.2`: 0.2.x renders Excel date cells with a Japanese-era number format (`[$-411]ge.m.d`, common in government xlsx) as serials (`19682`). `tests/test_office.py::test_anydoc_keeps_excel_dates_as_dates` guards this — rerun it before lifting the pin.
- `markitdown` uses explicit extras (`pdf,docx,pptx,xlsx,xls,outlook`), not `[all]`: `[all]` caps `youtube-transcript-api` at `<1.1` (whose fetch returns empty responses) and from 0.1.6 pulls a pre-release `azure-ai-contentunderstanding`. It is also pinned `<0.1.6` because 0.1.6+ scrambles the reading order of vertical (tategaki) Japanese PDFs. `parsers/sns/youtube.py` takes the instance API path (`YouTubeTranscriptApi(http_client=...)`) on youtube-transcript-api ≥1.2.
- `GeminiEmbeddingFunction` (`core/vector_db.py`) implements chromadb's `name`/`get_config`/`build_from_config`; collections created before this (legacy EF) still open and query fine.
