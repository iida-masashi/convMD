import subprocess
from unittest.mock import MagicMock, patch

from convmd.core.browser4 import get_html_with_browser4, is_available


def test_is_available_true_when_on_path():
    with patch("convmd.core.browser4.shutil.which", return_value="/usr/bin/browser4-cli"):
        assert is_available() is True


def test_is_available_false_when_missing():
    with patch("convmd.core.browser4.shutil.which", return_value=None):
        assert is_available() is False


def test_get_html_returns_none_when_not_available():
    with patch("convmd.core.browser4.shutil.which", return_value=None):
        assert get_html_with_browser4("https://example.com", timeout=10) is None


def _mock_run(
    goto_returncode=0,
    goto_stdout="- Page URL: https://example.com/",
    capture_returncode=0,
    export_returncode=0,
):
    calls = []

    def run(cmd, **kwargs):
        calls.append(cmd)
        result = MagicMock()
        if "goto" in cmd:
            result.returncode = goto_returncode
            result.stdout = goto_stdout
            result.stderr = ""
        elif "export" in cmd:
            result.returncode = export_returncode
            result.stdout = ""
            result.stderr = ""
            if export_returncode == 0:
                # Only the real CLI writes this file, and only after a prior
                # `capture` populated the page storage `export` reads from.
                assert any("capture" in c for c in calls), (
                    "export called before htmlsnapshot capture"
                )
                file_path = cmd[cmd.index("--file") + 1]
                with open(file_path, "w", encoding="utf-8") as fh:
                    fh.write("<html><body>hello</body></html>")
        elif "capture" in cmd:
            result.returncode = capture_returncode
            result.stdout = ""
            result.stderr = ""
        else:  # close
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
        return result

    run.calls = calls
    return run


def test_get_html_success():
    with (
        patch("convmd.core.browser4.shutil.which", return_value="/usr/bin/browser4-cli"),
        patch("convmd.core.browser4.subprocess.run", side_effect=_mock_run()),
    ):
        html = get_html_with_browser4("https://example.com", timeout=10)
    assert html == "<html><body>hello</body></html>"


def test_get_html_returns_none_on_chrome_error_page():
    run = _mock_run(goto_stdout="- Page URL: chrome-error://chromewebdata/")
    with (
        patch("convmd.core.browser4.shutil.which", return_value="/usr/bin/browser4-cli"),
        patch("convmd.core.browser4.subprocess.run", side_effect=run),
    ):
        html = get_html_with_browser4("https://bad.example", timeout=10)
    assert html is None


def test_get_html_returns_none_on_goto_failure():
    run = _mock_run(goto_returncode=1)
    with (
        patch("convmd.core.browser4.shutil.which", return_value="/usr/bin/browser4-cli"),
        patch("convmd.core.browser4.subprocess.run", side_effect=run),
    ):
        html = get_html_with_browser4("https://example.com", timeout=10)
    assert html is None


def test_get_html_returns_none_on_export_failure():
    run = _mock_run(export_returncode=1)
    with (
        patch("convmd.core.browser4.shutil.which", return_value="/usr/bin/browser4-cli"),
        patch("convmd.core.browser4.subprocess.run", side_effect=run),
    ):
        html = get_html_with_browser4("https://example.com", timeout=10)
    assert html is None


def test_get_html_returns_none_on_capture_failure():
    run = _mock_run(capture_returncode=1)
    with (
        patch("convmd.core.browser4.shutil.which", return_value="/usr/bin/browser4-cli"),
        patch("convmd.core.browser4.subprocess.run", side_effect=run),
    ):
        html = get_html_with_browser4("https://example.com", timeout=10)
    assert html is None


def test_get_html_calls_capture_before_export():
    run = _mock_run()
    with (
        patch("convmd.core.browser4.shutil.which", return_value="/usr/bin/browser4-cli"),
        patch("convmd.core.browser4.subprocess.run", side_effect=run),
    ):
        get_html_with_browser4("https://example.com", timeout=10)
    step_names = [
        "goto"
        if "goto" in c
        else "capture"
        if "capture" in c
        else "export"
        if "export" in c
        else "close"
        for c in run.calls
    ]
    assert step_names == ["goto", "capture", "export", "close"]


def test_get_html_closes_session_even_on_failure():
    close_calls = []

    def run(cmd, **kwargs):
        result = MagicMock()
        if "goto" in cmd:
            result.returncode = 1
            result.stdout = ""
            result.stderr = "boom"
        elif "close" in cmd:
            close_calls.append(cmd)
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
        return result

    with (
        patch("convmd.core.browser4.shutil.which", return_value="/usr/bin/browser4-cli"),
        patch("convmd.core.browser4.subprocess.run", side_effect=run),
    ):
        get_html_with_browser4("https://example.com", timeout=10)
    assert len(close_calls) == 1


def test_get_html_returns_none_on_timeout():
    def run(cmd, **kwargs):
        if "goto" in cmd:
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=10)
        result = MagicMock()
        result.returncode = 0
        return result

    with (
        patch("convmd.core.browser4.shutil.which", return_value="/usr/bin/browser4-cli"),
        patch("convmd.core.browser4.subprocess.run", side_effect=run),
    ):
        html = get_html_with_browser4("https://example.com", timeout=10)
    assert html is None
