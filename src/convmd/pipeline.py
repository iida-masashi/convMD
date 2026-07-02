"""Post-processing pipeline orchestrator: extract → transform → link → summary → dispatch."""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

from convmd.cli_args import RunConfig
from convmd.constants import Suffix
from convmd.core import cache, gemini
from convmd.core.transform import transform_markdown_with_gemini
from convmd.integrations.notebooklm import upload_to_notebooklm

logger = logging.getLogger(__name__)


_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".mp4", ".flac", ".ogg", ".aac"}


def process_target(
    target_str: str,
    target_path: Path,
    output_dir: Path,
    cfg: RunConfig | None = None,
) -> Path | None:
    """Process a single target URL or file — preserved as a stable public API for tests."""
    try:
        if target_path.exists() and target_path.is_file():
            logger.info(f"Processing local file: {target_path}")

            if target_path.suffix.lower() == ".md":
                dest_path = output_dir / target_path.name
                if target_path.resolve() != dest_path.resolve():
                    shutil.copy2(target_path, dest_path)
                    logger.info(f"Copied markdown file to {dest_path}")
                return dest_path

            if target_path.suffix.lower() in _AUDIO_EXTENSIONS:
                from convmd.parsers.media.audio import convert_audio_file

                return convert_audio_file(target_path, output_dir)

            from convmd.parsers.office import convert_office_file

            return convert_office_file(
                target_path,
                output_dir,
                ai_extract=cfg.ai_extract if cfg else False,
                schema=cfg.schema if cfg else None,
            )

        logger.info(f"Analyzing URL: {target_str}")
        from convmd.routing import dispatch_url

        # Note: dispatch_url handles its own saving, but returns no path for multi-file outputs.
        # We rely on the timestamp-based scan in extract_phase as a backup.
        dispatch_url(target_str, output_dir, cfg)
        return None
    except Exception:
        logger.exception(f"Failed to process target '{target_str}'")
        return None


def _is_pipeline_artifact(name: str) -> bool:
    return (
        name.endswith(Suffix.TRANSFORMED)
        or name.endswith(Suffix.LINKED)
        or name.endswith(Suffix.DIFF)
        or name == Suffix.SUMMARY
    )


def extract_phase(cfg: RunConfig, start_time: float) -> list[Path]:
    """Run parsers and return newly generated Markdown files."""
    target_path = Path(cfg.target)
    results: list[Path] = []

    if target_path.exists() and target_path.is_dir():
        logger.info(f"Detected directory input. Processing files recursively in: {target_path}")
        for file_path in target_path.rglob("*"):
            if file_path.is_file() and not any(part.startswith(".") for part in file_path.parts):
                p = process_target(str(file_path), file_path, cfg.output_dir, cfg)
                if p:
                    results.append(p)
    else:
        is_url = not (target_path.exists() and target_path.is_file())
        if is_url and cfg.depth > 0:
            logger.info(
                f"Depth > 0 specified. Crawling URLs from {cfg.target} up to depth {cfg.depth}..."
            )
            from convmd.core.crawler import crawl_urls

            crawled = crawl_urls(cfg.target, cfg.depth)
            for url in crawled:
                p = process_target(url, Path(url), cfg.output_dir, cfg)
                if p:
                    results.append(p)
        else:
            p = process_target(cfg.target, target_path, cfg.output_dir, cfg)
            if p:
                results.append(p)

    # Backup: scan for newly created files (handles multi-file outputs like crawling)
    new_md_set: set[Path] = {p for p in results if p.suffix.lower() == ".md"}
    for md_file in cfg.output_dir.rglob("*.md"):
        if md_file.is_file() and md_file.stat().st_mtime >= start_time:
            if not _is_pipeline_artifact(md_file.name):
                new_md_set.add(md_file)

    new_md = sorted(new_md_set)
    logger.info(f"Found {len(new_md)} generated markdown files for pipeline processing.")
    return new_md


def transform_phase(files: list[Path], cfg: RunConfig) -> list[Path]:
    if not cfg.transform:
        return list(files)
    out: list[Path] = []
    for md_file in files:
        transformed = transform_markdown_with_gemini(md_file, cfg.transform)
        out.append(transformed if transformed else md_file)
    return out


def link_phase(files: list[Path], cfg: RunConfig) -> list[Path]:
    if not cfg.auto_link:
        return list(files)
    from convmd.core.transform import apply_obsidian_links

    vault = cfg.obsidian_vault if cfg.normalize_tags else None
    out: list[Path] = []
    for md_file in files:
        linked = apply_obsidian_links(
            md_file,
            vault_path=vault,
            tag_similarity_cutoff=cfg.tag_similarity_cutoff,
        )
        out.append(linked if linked else md_file)
    return out


def summary_phase(files: list[Path], cfg: RunConfig) -> Path | None:
    if not (cfg.summary and files):
        return None
    from convmd.core.transform import generate_executive_summary

    combined = ""
    for md_file in files:
        combined += f"\n\n--- Source: {md_file.name} ---\n\n"
        combined += md_file.read_text(encoding="utf-8")
    return generate_executive_summary(combined, cfg.output_dir)


def embed_phase(files: list[Path], cfg: RunConfig) -> None:
    """Upsert generated markdown files into ChromaDB for semantic search."""
    valid_files = [f for f in files if f.exists() and not f.name.endswith(Suffix.DIFF)]
    if not valid_files:
        return

    try:
        from convmd.core.vector_db import ChromaManager
        manager = ChromaManager(cfg.output_dir)
        for path in valid_files:
            try:
                body = path.read_text(encoding="utf-8")
                manager.upsert_document(path, body)
            except OSError as e:
                logger.warning(f"Could not read {path.name} for embedding: {e}")
    except ImportError:
        logger.warning("chromadb not installed. Skipping embedding phase.")
    except Exception as e:
        logger.error(f"Embedding phase failed: {e}")


def dispatch_phase(files: list[Path], summary_path: Path | None, cfg: RunConfig) -> None:
    import os

    obsidian_api_url = os.environ.get("OBSIDIAN_REST_API_URL")
    obsidian_api_key = os.environ.get("OBSIDIAN_REST_API_KEY")

    if obsidian_api_url and obsidian_api_key:
        from convmd.integrations.obsidian_rest import export_to_obsidian_api

        for md_file in files:
            logger.info(f"Exporting to Obsidian via API: {md_file.name}")
            export_to_obsidian_api(md_file, obsidian_api_url, obsidian_api_key, target_folder="Clippings")

    notion_api_token = os.environ.get("NOTION_API_TOKEN")
    notion_database_id = os.environ.get("NOTION_DATABASE_ID")

    if notion_api_token and notion_database_id:
        from convmd.integrations.notion import export_to_notion

        for md_file in files:
            logger.info(f"Exporting to Notion: {md_file.name}")
            export_to_notion(md_file, notion_api_token, notion_database_id)

    if cfg.slack_webhook and summary_path and summary_path.exists():
        from convmd.integrations.slack import send_to_slack

        send_to_slack(cfg.slack_webhook, summary_path.read_text(encoding="utf-8"))

    if cfg.notebooklm:
        for md_file in files:
            upload_to_notebooklm(cfg.notebooklm, md_file)

    if cfg.format != "md" and files:
        try:
            from convmd.exporters import export_files

            export_files(cfg.format, files, cfg.output_dir)
        except Exception as e:
            logger.warning(f"Export to {cfg.format} failed: {e}")

    if cfg.open_obsidian:
        if cfg.obsidian_vault:
            from convmd.integrations.obsidian import open_in_obsidian

            open_in_obsidian(cfg.obsidian_vault)
        else:
            logger.warning(
                "To use --open-obsidian, please provide the path to your vault with --obsidian-vault."
            )


def diff_phase(files: list[Path], cfg: RunConfig) -> list[Path]:
    """Compare each newly-generated Markdown body against the cached previous version.

    For each changed file:
      * always record the new body in the cache
      * if cfg.diff_only is True, write a sibling ``*_diff.md`` containing the unified diff
    Files whose content hash matches the previous version are skipped silently.
    """
    if cfg.no_cache:
        return list(files)

    survivors: list[Path] = []
    for path in files:
        try:
            body = path.read_text(encoding="utf-8")
        except OSError:
            survivors.append(path)
            continue

        prev_hash, prev_body = cache.get_previous(cfg.output_dir, str(path))
        new_hash = cache.hash_text(body)
        if prev_hash == new_hash:
            logger.info(f"No content change for {path.name}; skipping downstream.")
            continue

        if cfg.diff_only and prev_body is not None:
            diff_text = cache.diff(prev_body, body, url=str(path))
            if diff_text:
                diff_path = path.parent / f"{path.stem}{Suffix.DIFF}"
                diff_path.write_text(diff_text + "\n", encoding="utf-8")
                logger.info(f"Wrote diff to {diff_path}")
                survivors.append(diff_path)

        cache.record(
            cfg.output_dir,
            str(path),
            body=body,
            output_path=path,
            etag=None,
            last_modified=None,
        )
        survivors.append(path)
    return survivors


def run_once(cfg: RunConfig) -> None:
    start_time = time.time()
    files = extract_phase(cfg, start_time)
    files = diff_phase(files, cfg) if not cfg.no_cache else files
    files = transform_phase(files, cfg)
    files = link_phase(files, cfg)
    files_with_summary = list(files)
    summary_path = summary_phase(files, cfg)
    if summary_path:
        files_with_summary.append(summary_path)
    embed_phase(files_with_summary, cfg)
    dispatch_phase(files_with_summary, summary_path, cfg)


def run_pipeline(cfg: RunConfig) -> None:
    """Run the pipeline once, or repeatedly when ``cfg.interval > 0``."""
    if cfg.interval > 0:
        logger.info(f"Starting daemon mode. Running pipeline every {cfg.interval} minutes.")
        try:
            while True:
                run_once(cfg)
                logger.info(f"Sleeping for {cfg.interval} minutes...")
                time.sleep(cfg.interval * 60)
        except KeyboardInterrupt:
            logger.info("Daemon mode stopped by user.")
    else:
        run_once(cfg)
        if cfg.show_cost and not gemini.usage_tracker().is_empty():
            _print_cost_summary()


_PRICE_USD_PER_1M_TOKENS = {
    "gemini-3.1-pro-preview": (1.25, 5.00),
    "gemini-3-flash-preview": (0.075, 0.30),
}


def _print_cost_summary() -> None:
    tracker = gemini.usage_tracker()
    total = 0.0
    print("\n[Cost]")
    for model, usage in tracker.by_model.items():
        in_rate, out_rate = _PRICE_USD_PER_1M_TOKENS.get(model, (0.0, 0.0))
        cost = (usage.input_tokens * in_rate + usage.output_tokens * out_rate) / 1_000_000
        total += cost
        print(
            f"  {model}: calls={usage.calls} "
            f"in={usage.input_tokens} out={usage.output_tokens} ≈ ${cost:.4f}"
        )
    if total:
        print(f"  total ≈ ${total:.4f}")
