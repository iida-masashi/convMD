import argparse
from unittest.mock import MagicMock, patch

from convmd.commands.doctor_cmd import run_doctor


def _args():
    return argparse.Namespace()


def test_python_version_ok(capsys):
    run_doctor(_args())
    out = capsys.readouterr().out
    assert "[OK] Python version" in out


def test_pandoc_found(capsys):
    with patch("convmd.commands.doctor_cmd.shutil.which", return_value="/usr/bin/pandoc"):
        run_doctor(_args())
    out = capsys.readouterr().out
    assert "[OK] pandoc found: /usr/bin/pandoc" in out


def test_pandoc_missing(capsys):
    with patch("convmd.commands.doctor_cmd.shutil.which", return_value=None):
        run_doctor(_args())
    out = capsys.readouterr().out
    assert "[MISSING] pandoc not found on PATH" in out
    assert "epub/pdf/docx/html" in out


def test_ffmpeg_missing(capsys):
    def which(name):
        return None

    with patch("convmd.commands.doctor_cmd.shutil.which", side_effect=which):
        run_doctor(_args())
    out = capsys.readouterr().out
    assert "[MISSING] ffmpeg not found on PATH" in out


def test_ffmpeg_found(capsys):
    def which(name):
        return f"/usr/bin/{name}" if name == "ffmpeg" else None

    with patch("convmd.commands.doctor_cmd.shutil.which", side_effect=which):
        run_doctor(_args())
    out = capsys.readouterr().out
    assert "[OK] ffmpeg found: /usr/bin/ffmpeg" in out


def test_gemini_key_missing(capsys, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    run_doctor(_args())
    out = capsys.readouterr().out
    assert "[MISSING] GEMINI_API_KEY / GOOGLE_API_KEY not set" in out


def test_gemini_key_found_via_gemini_api_key(capsys, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    run_doctor(_args())
    out = capsys.readouterr().out
    assert "[OK] Gemini API key found (via GEMINI_API_KEY)" in out


def test_gemini_key_found_via_google_api_key(capsys, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    run_doctor(_args())
    out = capsys.readouterr().out
    assert "[OK] Gemini API key found (via GOOGLE_API_KEY)" in out


def test_optional_extras_all_missing(capsys):
    with patch("convmd.commands.doctor_cmd._is_installed", return_value=False):
        run_doctor(_args())
    out = capsys.readouterr().out
    assert "[MISSING] faster_whisper not installed" in out
    assert "uv sync --extra whisper" in out
    assert "[MISSING] playwright not installed" in out
    assert "uv sync --extra render" in out
    assert "[MISSING] notebooklm_py not installed" in out
    assert "uv sync --extra notebooklm" in out
    assert "[MISSING] PIL not installed" in out
    assert "uv sync --extra image" in out
    assert "[MISSING] yt_dlp not installed" in out
    assert "uv sync --extra scripts" in out
    # playwright not installed -> no browser-binary check line at all
    assert "browser binaries" not in out


def test_optional_extras_all_installed(capsys):
    with patch("convmd.commands.doctor_cmd._is_installed", return_value=True), patch(
        "convmd.commands.doctor_cmd._check_playwright_browsers", return_value=None
    ):
        run_doctor(_args())
    out = capsys.readouterr().out
    assert "[OK] faster_whisper installed" in out
    assert "[OK] playwright installed" in out
    assert "[OK] notebooklm_py installed" in out
    assert "[OK] PIL installed" in out
    assert "[OK] yt_dlp installed" in out


def test_playwright_browsers_installed(capsys):
    mock_browser = MagicMock()
    mock_chromium = MagicMock(executable_path="/fake/chrome")
    mock_chromium.launch.return_value = mock_browser
    mock_pw = MagicMock(chromium=mock_chromium)
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_pw)
    mock_ctx.__exit__ = MagicMock(return_value=False)

    with patch("convmd.commands.doctor_cmd._is_installed", return_value=True), patch(
        "playwright.sync_api.sync_playwright", return_value=mock_ctx
    ), patch("convmd.commands.doctor_cmd.Path.exists", return_value=True):
        run_doctor(_args())
    out = capsys.readouterr().out
    assert "[OK] playwright browser binaries found and launchable" in out
    mock_chromium.launch.assert_called_once_with(headless=True)
    mock_browser.close.assert_called_once()


def test_playwright_browsers_missing(capsys):
    mock_chromium = MagicMock(executable_path="/fake/chrome")
    mock_pw = MagicMock(chromium=mock_chromium)
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_pw)
    mock_ctx.__exit__ = MagicMock(return_value=False)

    with patch("convmd.commands.doctor_cmd._is_installed", return_value=True), patch(
        "playwright.sync_api.sync_playwright", return_value=mock_ctx
    ), patch("convmd.commands.doctor_cmd.Path.exists", return_value=False):
        run_doctor(_args())
    out = capsys.readouterr().out
    assert "[WARN] playwright installed but browser binaries missing" in out
    assert "playwright install chromium" in out
    mock_chromium.launch.assert_not_called()


def test_playwright_browsers_present_but_launch_fails(capsys):
    """Covers the case a plain executable_path check can't catch: the binary exists
    on disk but is a stale/mismatched revision that fails to actually launch."""
    mock_chromium = MagicMock(executable_path="/fake/chrome")
    mock_chromium.launch.side_effect = RuntimeError("Executable doesn't exist at revision path")
    mock_pw = MagicMock(chromium=mock_chromium)
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_pw)
    mock_ctx.__exit__ = MagicMock(return_value=False)

    with patch("convmd.commands.doctor_cmd._is_installed", return_value=True), patch(
        "playwright.sync_api.sync_playwright", return_value=mock_ctx
    ), patch("convmd.commands.doctor_cmd.Path.exists", return_value=True):
        run_doctor(_args())
    out = capsys.readouterr().out
    assert "[WARN] playwright browser binary found but failed to launch" in out
    assert "playwright install chromium" in out


def test_playwright_not_installed_skips_browser_check(capsys):
    with patch("convmd.commands.doctor_cmd._is_installed", return_value=False):
        run_doctor(_args())
    out = capsys.readouterr().out
    assert "browser binaries" not in out


def test_browser4_cli_found(capsys):
    def which(name):
        return f"/usr/bin/{name}" if name == "browser4-cli" else None

    with patch("convmd.commands.doctor_cmd.shutil.which", side_effect=which):
        run_doctor(_args())
    out = capsys.readouterr().out
    assert "[OK] browser4-cli found: /usr/bin/browser4-cli" in out


def test_browser4_cli_missing(capsys):
    with patch("convmd.commands.doctor_cmd.shutil.which", return_value=None):
        run_doctor(_args())
    out = capsys.readouterr().out
    assert "[MISSING] browser4-cli not found on PATH" in out
    assert "npm install -g browser4-cli" in out


def test_config_files_none_found(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("convmd.commands.doctor_cmd.Path.home", lambda: tmp_path / "home")
    monkeypatch.setattr("convmd.commands.doctor_cmd.Path.cwd", lambda: tmp_path / "cwd")
    with patch("convmd.commands.doctor_cmd.load_config", return_value={}):
        run_doctor(_args())
    out = capsys.readouterr().out
    assert "[MISSING] ~/.convmd.yaml not found" in out
    assert "[MISSING] ./.convmd.yaml not found" in out
    assert "obsidian_vault is set" not in out


def test_config_files_found_with_obsidian_vault_warns(tmp_path, capsys, monkeypatch):
    cwd_dir = tmp_path / "cwd"
    cwd_dir.mkdir()
    (cwd_dir / ".convmd.yaml").write_text("obsidian_vault: /some/vault\n", encoding="utf-8")
    monkeypatch.setattr("convmd.commands.doctor_cmd.Path.home", lambda: tmp_path / "home")
    monkeypatch.setattr("convmd.commands.doctor_cmd.Path.cwd", lambda: cwd_dir)

    with patch(
        "convmd.commands.doctor_cmd.load_config",
        return_value={"obsidian_vault": "/some/vault"},
    ):
        run_doctor(_args())
    out = capsys.readouterr().out
    assert "[OK] ./.convmd.yaml found" in out
    assert "merged config keys: obsidian_vault" in out
    assert "[WARN] obsidian_vault is set in config" in out
    assert "takes precedence over --output-dir" in out


def test_config_files_found_without_obsidian_vault_no_warning(tmp_path, capsys, monkeypatch):
    cwd_dir = tmp_path / "cwd"
    cwd_dir.mkdir()
    (cwd_dir / ".convmd.yaml").write_text("auto_link: true\n", encoding="utf-8")
    monkeypatch.setattr("convmd.commands.doctor_cmd.Path.home", lambda: tmp_path / "home")
    monkeypatch.setattr("convmd.commands.doctor_cmd.Path.cwd", lambda: cwd_dir)

    with patch(
        "convmd.commands.doctor_cmd.load_config",
        return_value={"auto_link": True},
    ):
        run_doctor(_args())
    out = capsys.readouterr().out
    assert "merged config keys: auto_link" in out
    assert "obsidian_vault is set" not in out


def test_output_dir_env_set(capsys, monkeypatch):
    monkeypatch.setenv("CONVMD_OUTPUT_DIR", "/some/output")
    run_doctor(_args())
    out = capsys.readouterr().out
    assert "[OK] CONVMD_OUTPUT_DIR set: /some/output" in out


def test_output_dir_env_missing(capsys, monkeypatch):
    monkeypatch.delenv("CONVMD_OUTPUT_DIR", raising=False)
    run_doctor(_args())
    out = capsys.readouterr().out
    assert "[MISSING] CONVMD_OUTPUT_DIR not set" in out


def test_report_header_printed(capsys):
    run_doctor(_args())
    out = capsys.readouterr().out
    assert "convmd doctor" in out
