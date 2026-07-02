"""Branch tests for pipeline phases (process_target / extract / dispatch / diff / run_pipeline)."""

from pathlib import Path
from unittest.mock import patch

from convmd import pipeline
from convmd.cli_args import RunConfig


def _cfg(target, output_dir, **overrides) -> RunConfig:
    cfg = RunConfig(target=str(target), output_dir=output_dir)
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


# --- process_target ---

def test_process_target_local_md_copies_to_output(tmp_path):
    src = tmp_path / "in.md"
    src.write_text("# X", encoding="utf-8")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    p = pipeline.process_target(str(src), src, out_dir)
    assert p == out_dir / "in.md"
    assert p.read_text(encoding="utf-8") == "# X"


def test_process_target_local_md_same_dir_no_copy(tmp_path):
    src = tmp_path / "in.md"
    src.write_text("# X", encoding="utf-8")
    p = pipeline.process_target(str(src), src, tmp_path)
    assert p == tmp_path / "in.md"


@patch("convmd.parsers.media.audio.convert_audio_file")
def test_process_target_audio_dispatch(mock_audio, tmp_path):
    src = tmp_path / "voice.mp3"
    src.write_bytes(b"\x00")
    out = tmp_path / "ret.md"
    mock_audio.return_value = out
    p = pipeline.process_target(str(src), src, tmp_path)
    assert p == out
    mock_audio.assert_called_once()


@patch("convmd.parsers.office.convert_office_file")
def test_process_target_office_dispatch(mock_office, tmp_path):
    src = tmp_path / "doc.pdf"
    src.write_bytes(b"\x00")
    out = tmp_path / "ret.md"
    mock_office.return_value = out
    cfg = _cfg(src, tmp_path, ai_extract=True, schema='{"k":"v"}')
    p = pipeline.process_target(str(src), src, tmp_path, cfg)
    assert p == out
    _, kwargs = mock_office.call_args
    assert kwargs["ai_extract"] is True
    assert kwargs["schema"] == '{"k":"v"}'


@patch("convmd.routing.dispatch_url")
def test_process_target_url_routes_to_dispatch(mock_dispatch, tmp_path):
    p = pipeline.process_target("https://example.com", Path("https://example.com"), tmp_path)
    assert p is None
    mock_dispatch.assert_called_once()


@patch("convmd.parsers.office.convert_office_file", side_effect=RuntimeError("boom"))
def test_process_target_swallows_exception(_mock_office, tmp_path):
    src = tmp_path / "doc.pdf"
    src.write_bytes(b"\x00")
    assert pipeline.process_target(str(src), src, tmp_path) is None


# --- extract_phase ---

def test_extract_phase_directory(tmp_path):
    indir = tmp_path / "in"
    indir.mkdir()
    f = indir / "a.md"
    f.write_text("# A", encoding="utf-8")
    outdir = tmp_path / "out"
    outdir.mkdir()
    cfg = _cfg(indir, outdir)
    files = pipeline.extract_phase(cfg, start_time=0)
    assert any(p.name == "a.md" for p in files)


@patch("convmd.core.crawler.crawl_urls", return_value=["https://x/", "https://y/"])
@patch("convmd.routing.dispatch_url")
def test_extract_phase_url_with_depth_uses_crawler(mock_dispatch, _mock_crawl, tmp_path):
    outdir = tmp_path / "out"
    outdir.mkdir()
    cfg = _cfg("https://example.com", outdir, depth=2)
    pipeline.extract_phase(cfg, start_time=0)
    assert mock_dispatch.call_count == 2


def test_extract_phase_backup_scan_picks_up_newly_created_files(tmp_path):
    outdir = tmp_path / "out"
    outdir.mkdir()
    cfg = _cfg("https://example.com", outdir, depth=0)
    with patch("convmd.routing.dispatch_url") as mock_dispatch:
        def side(*_a, **_k):
            (outdir / "generated.md").write_text("body", encoding="utf-8")
        mock_dispatch.side_effect = side
        files = pipeline.extract_phase(cfg, start_time=0)
    assert any(p.name == "generated.md" for p in files)


def test_extract_phase_skips_pipeline_artifacts(tmp_path):
    outdir = tmp_path / "out"
    outdir.mkdir()
    (outdir / "x_transformed.md").write_text("t", encoding="utf-8")
    (outdir / "x_diff.md").write_text("d", encoding="utf-8")
    (outdir / "real.md").write_text("r", encoding="utf-8")

    cfg = _cfg("https://example.com", outdir)
    with patch("convmd.routing.dispatch_url"):
        files = pipeline.extract_phase(cfg, start_time=0)
    names = {p.name for p in files}
    assert "real.md" in names
    assert "x_transformed.md" not in names
    assert "x_diff.md" not in names


# --- transform_phase ---

@patch("convmd.pipeline.transform_markdown_with_gemini")
def test_transform_phase_skipped_when_no_instruction(mock_t, tmp_path):
    cfg = _cfg("x", tmp_path)
    files = [tmp_path / "a.md"]
    out = pipeline.transform_phase(files, cfg)
    assert out == files
    mock_t.assert_not_called()


@patch("convmd.pipeline.transform_markdown_with_gemini")
def test_transform_phase_uses_original_on_failure(mock_t, tmp_path):
    cfg = _cfg("x", tmp_path, transform="Translate")
    f = tmp_path / "a.md"
    f.write_text("x", encoding="utf-8")
    mock_t.return_value = None
    out = pipeline.transform_phase([f], cfg)
    assert out == [f]


@patch("convmd.pipeline.transform_markdown_with_gemini")
def test_transform_phase_replaces_with_transformed(mock_t, tmp_path):
    cfg = _cfg("x", tmp_path, transform="Translate")
    f = tmp_path / "a.md"
    transformed = tmp_path / "a_transformed.md"
    mock_t.return_value = transformed
    out = pipeline.transform_phase([f], cfg)
    assert out == [transformed]


# --- link_phase ---

def test_link_phase_skipped_when_no_auto_link(tmp_path):
    cfg = _cfg("x", tmp_path, auto_link=False)
    files = [tmp_path / "a.md"]
    assert pipeline.link_phase(files, cfg) == files


@patch("convmd.core.transform.apply_obsidian_links")
def test_link_phase_runs_when_enabled(mock_link, tmp_path):
    cfg = _cfg("x", tmp_path, auto_link=True)
    f = tmp_path / "a.md"
    linked = tmp_path / "a_linked.md"
    mock_link.return_value = linked
    out = pipeline.link_phase([f], cfg)
    assert out == [linked]


# --- summary_phase ---

def test_summary_phase_skipped_when_disabled(tmp_path):
    cfg = _cfg("x", tmp_path, summary=False)
    assert pipeline.summary_phase([tmp_path / "a.md"], cfg) is None


def test_summary_phase_skipped_when_no_files(tmp_path):
    cfg = _cfg("x", tmp_path, summary=True)
    assert pipeline.summary_phase([], cfg) is None


@patch("convmd.core.transform.generate_executive_summary")
def test_summary_phase_combines_files(mock_summary, tmp_path):
    cfg = _cfg("x", tmp_path, summary=True)
    a = tmp_path / "a.md"
    a.write_text("alpha", encoding="utf-8")
    b = tmp_path / "b.md"
    b.write_text("beta", encoding="utf-8")
    pipeline.summary_phase([a, b], cfg)
    mock_summary.assert_called_once()
    combined = mock_summary.call_args[0][0]
    assert "alpha" in combined
    assert "beta" in combined


# --- dispatch_phase ---

@patch("convmd.integrations.obsidian_rest.export_to_obsidian_api")
def test_dispatch_obsidian_rest_branch(mock_export, tmp_path, monkeypatch):
    monkeypatch.setenv("OBSIDIAN_REST_API_URL", "https://localhost:27124")
    monkeypatch.setenv("OBSIDIAN_REST_API_KEY", "secret")
    cfg = _cfg("x", tmp_path)
    files = [tmp_path / "a.md", tmp_path / "b.md"]
    pipeline.dispatch_phase(files, None, cfg)
    assert mock_export.call_count == 2


@patch("convmd.integrations.notion.export_to_notion")
def test_dispatch_notion_branch(mock_export, tmp_path, monkeypatch):
    monkeypatch.setenv("NOTION_API_TOKEN", "secret-token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-123")
    cfg = _cfg("x", tmp_path)
    files = [tmp_path / "a.md", tmp_path / "b.md"]
    pipeline.dispatch_phase(files, None, cfg)
    assert mock_export.call_count == 2
    mock_export.assert_any_call(files[0], "secret-token", "db-123")


@patch("convmd.integrations.slack.send_to_slack")
def test_dispatch_slack_branch(mock_slack, tmp_path, monkeypatch):
    monkeypatch.delenv("OBSIDIAN_REST_API_URL", raising=False)
    monkeypatch.delenv("OBSIDIAN_REST_API_KEY", raising=False)
    monkeypatch.delenv("NOTION_API_TOKEN", raising=False)
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)
    cfg = _cfg("x", tmp_path, slack_webhook="https://hooks.slack/")
    summary = tmp_path / "summary.md"
    summary.write_text("hello", encoding="utf-8")
    pipeline.dispatch_phase([], summary, cfg)
    mock_slack.assert_called_once()
    args, _ = mock_slack.call_args
    assert args[0] == "https://hooks.slack/"
    assert args[1] == "hello"


@patch("convmd.pipeline.upload_to_notebooklm")
def test_dispatch_notebooklm_branch(mock_upload, tmp_path, monkeypatch):
    monkeypatch.delenv("OBSIDIAN_REST_API_URL", raising=False)
    cfg = _cfg("x", tmp_path, notebooklm="nb-123")
    files = [tmp_path / "a.md", tmp_path / "b.md"]
    pipeline.dispatch_phase(files, None, cfg)
    assert mock_upload.call_count == 2


@patch("convmd.exporters.export_files")
def test_dispatch_export_branch(mock_export, tmp_path, monkeypatch):
    monkeypatch.delenv("OBSIDIAN_REST_API_URL", raising=False)
    cfg = _cfg("x", tmp_path, format="json")
    files = [tmp_path / "a.md"]
    pipeline.dispatch_phase(files, None, cfg)
    mock_export.assert_called_once_with("json", files, tmp_path)


@patch("convmd.exporters.export_files", side_effect=RuntimeError("export boom"))
def test_dispatch_export_swallows_failure(_mock_export, tmp_path, monkeypatch):
    monkeypatch.delenv("OBSIDIAN_REST_API_URL", raising=False)
    cfg = _cfg("x", tmp_path, format="epub")
    pipeline.dispatch_phase([tmp_path / "a.md"], None, cfg)


@patch("convmd.integrations.obsidian.open_in_obsidian")
def test_dispatch_open_obsidian_with_vault(mock_open, tmp_path, monkeypatch):
    monkeypatch.delenv("OBSIDIAN_REST_API_URL", raising=False)
    vault = tmp_path / "MyVault"
    cfg = _cfg("x", tmp_path, open_obsidian=True, obsidian_vault=vault)
    pipeline.dispatch_phase([], None, cfg)
    mock_open.assert_called_once_with(vault)


def test_dispatch_open_obsidian_without_vault_warns(tmp_path, monkeypatch, caplog):
    monkeypatch.delenv("OBSIDIAN_REST_API_URL", raising=False)
    cfg = _cfg("x", tmp_path, open_obsidian=True, obsidian_vault=None)
    pipeline.dispatch_phase([], None, cfg)
    assert any("obsidian-vault" in r.message for r in caplog.records if r.levelname == "WARNING")


# --- diff_phase ---

def test_diff_phase_no_cache_skips(tmp_path):
    cfg = _cfg("x", tmp_path, no_cache=True)
    files = [tmp_path / "a.md"]
    assert pipeline.diff_phase(files, cfg) == files


def test_diff_phase_records_and_returns_changed(tmp_path):
    outdir = tmp_path / "out"
    outdir.mkdir()
    md = outdir / "page.md"
    md.write_text("v1", encoding="utf-8")
    cfg = _cfg("x", outdir)
    out = pipeline.diff_phase([md], cfg)
    assert md in out


def test_diff_phase_skips_unchanged(tmp_path):
    outdir = tmp_path / "out"
    outdir.mkdir()
    md = outdir / "page.md"
    md.write_text("v1", encoding="utf-8")
    cfg = _cfg("x", outdir)
    pipeline.diff_phase([md], cfg)
    out = pipeline.diff_phase([md], cfg)
    assert md not in out


def test_diff_phase_writes_diff_when_diff_only(tmp_path):
    outdir = tmp_path / "out"
    outdir.mkdir()
    md = outdir / "page.md"
    md.write_text("v1", encoding="utf-8")
    cfg = _cfg("x", outdir, diff_only=True)
    pipeline.diff_phase([md], cfg)
    md.write_text("v2\n", encoding="utf-8")
    out = pipeline.diff_phase([md], cfg)
    diff_path = md.parent / "page_diff.md"
    assert diff_path.exists()
    assert diff_path in out


# --- run_pipeline ---

@patch("convmd.pipeline.dispatch_phase")
@patch("convmd.pipeline.summary_phase", return_value=None)
@patch("convmd.pipeline.link_phase", side_effect=lambda f, _c: f)
@patch("convmd.pipeline.transform_phase", side_effect=lambda f, _c: f)
@patch("convmd.pipeline.diff_phase", side_effect=lambda f, _c: f)
@patch("convmd.pipeline.extract_phase", return_value=[])
def test_run_pipeline_once(mock_extract, *_others, **__):
    cfg = RunConfig(target="x", output_dir=Path("."), interval=0)
    pipeline.run_pipeline(cfg)
    mock_extract.assert_called_once()


@patch("convmd.pipeline.run_once")
@patch("convmd.pipeline.time.sleep", side_effect=KeyboardInterrupt)
def test_run_pipeline_daemon_stops_on_interrupt(_mock_sleep, mock_run_once, tmp_path):
    cfg = RunConfig(target="x", output_dir=tmp_path, interval=5)
    pipeline.run_pipeline(cfg)
    assert mock_run_once.call_count == 1
