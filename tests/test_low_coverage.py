"""Coverage-raising tests for modules previously under 50%."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from convmd.exporters import export_files, get_exporter
from convmd.exporters.pandoc_exporter import PandocExporter
from convmd.integrations import notebooklm, obsidian
from convmd.parsers import general
from convmd.parsers.sns import youtube

# --- parsers/general.py ---

@patch("convmd.parsers.general.process_images", side_effect=lambda body, *_a, **_k: body)
@patch("convmd.parsers.general.fetch_html")
def test_general_website_success(mock_fetch, _mock_imgs, tmp_path):
    mock_fetch.return_value = (
        "<html><head><title>Page</title></head>"
        "<body><article><h1>Page</h1><p>Article body content paragraph. This paragraph needs to be long enough to pass the length check. Let's add some more words here so that the extracted markdown is definitely longer than 100 characters. That should do the trick and fix the test failure.</p></article></body></html>"
    )
    out = general.convert_general_website("https://example.com/p", tmp_path)
    assert out is not None
    text = out.read_text(encoding="utf-8")
    assert "Article body content" in text
    assert '- "general"' in text


@patch("convmd.parsers.general.fetch_html", return_value=None)
def test_general_website_fetch_failure(_mock_fetch, tmp_path):
    assert general.convert_general_website("https://example.com/p", tmp_path) is None


# --- parsers/sns/youtube.convert_youtube end-to-end ---

@patch("convmd.parsers.sns.youtube.process_images", side_effect=lambda body, *_a, **_k: body)
@patch("convmd.parsers.sns.youtube.fetch_chapters", return_value=[])
@patch("convmd.parsers.sns.youtube.get_video_title", return_value="My Video")
@patch("convmd.parsers.sns.youtube._fetch_transcript")
def test_convert_youtube_no_chapters(mock_transcript, *_ignored, **__):
    transcript = [{"start": 0.0, "text": "hello"}, {"start": 5.0, "text": "world"}]
    mock_transcript.return_value = transcript

    import tempfile

    with tempfile.TemporaryDirectory() as td:
        out = youtube.convert_youtube("https://youtu.be/abcdefghijk", Path(td))
        assert out is not None
        text = out.read_text(encoding="utf-8")
        assert "hello" in text
        assert "world" in text
        assert '- "youtube"' in text


@patch("convmd.parsers.sns.youtube.process_images", side_effect=lambda body, *_a, **_k: body)
@patch("convmd.parsers.sns.youtube.fetch_chapters",
       return_value=[(0.0, "Intro"), (3.0, "Mid")])
@patch("convmd.parsers.sns.youtube.get_video_title", return_value="Chaptered")
@patch("convmd.parsers.sns.youtube._fetch_transcript")
def test_convert_youtube_with_chapters(mock_transcript, *_ignored, **__):
    transcript = [
        {"start": 0.0, "text": "first"},
        {"start": 3.5, "text": "second"},
    ]
    mock_transcript.return_value = transcript

    import tempfile

    with tempfile.TemporaryDirectory() as td:
        out = youtube.convert_youtube("https://youtu.be/abcdefghijk", Path(td))
        assert out is not None
        text = out.read_text(encoding="utf-8")
        assert "## [00:00] Intro" in text
        assert "## [00:03] Mid" in text


def test_convert_youtube_bad_url(tmp_path):
    # No 11-char video id in the URL
    assert youtube.convert_youtube("https://youtube.com/", tmp_path) is None


@patch("convmd.parsers.sns.youtube._fetch_transcript", return_value=None)
def test_convert_youtube_no_transcript(_mock_t, tmp_path):
    assert youtube.convert_youtube("https://youtu.be/abcdefghijk", tmp_path) is None


@patch("convmd.parsers.sns.youtube.get_client")
def test_get_video_title_success(mock_get_client):
    mock_response = MagicMock()
    mock_response.json.return_value = {"title": "Greatest Video"}
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_get_client.return_value = mock_client

    assert youtube.get_video_title("abc12345678") == "Greatest Video"


@patch("convmd.parsers.sns.youtube.get_client", side_effect=Exception("boom"))
def test_get_video_title_fallback(_mock_client):
    assert youtube.get_video_title("xyz12345678").startswith("YouTube_Video_")


def test_get_video_id():
    assert youtube.get_video_id("https://youtu.be/abcdefghijk") == "abcdefghijk"
    assert youtube.get_video_id("https://youtube.com/watch?v=abcdefghijk") == "abcdefghijk"
    assert youtube.get_video_id("not-a-url") is None


def test_format_time():
    assert youtube.format_time(65) == "01:05"
    assert youtube.format_time(3725) == "1:02:05"


def test_load_cookies_skips_when_missing(tmp_path, monkeypatch):
    """When cookies.txt isn't present we silently no-op."""
    monkeypatch.chdir(tmp_path)
    import requests

    session = requests.Session()
    youtube._load_cookies(session)  # Should not raise
    assert len(session.cookies) == 0


def test_load_cookies_loads_when_present(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cookies = tmp_path / "cookies.txt"
    cookies.write_text(
        "# Netscape HTTP Cookie File\n"
        ".example.com\tTRUE\t/\tFALSE\t0\tname\tvalue\n",
        encoding="utf-8",
    )
    import requests

    session = requests.Session()
    youtube._load_cookies(session)  # Should not raise


# --- integrations/notebooklm ---

def test_notebooklm_handles_missing_dependency_gracefully(tmp_path, monkeypatch):
    """If notebooklm_py isn't importable, function should return without raising."""
    import sys
    # Simulate the import failing by inserting a sentinel that raises ImportError
    monkeypatch.setitem(sys.modules, "notebooklm_py", None)
    notebooklm.upload_to_notebooklm("nb-id", tmp_path / "fake.md")


@patch.dict("sys.modules", {"notebooklm_py": MagicMock()})
def test_notebooklm_upload_success(tmp_path):
    import sys

    fake_module = sys.modules["notebooklm_py"]
    fake_client = MagicMock()
    fake_client.upload_file.return_value = MagicMock(id="src-123")
    fake_module.NotebookLMClient.return_value = fake_client

    notebooklm.upload_to_notebooklm("nb-id", tmp_path / "file.md")
    fake_client.upload_file.assert_called_once()


@patch.dict("sys.modules", {"notebooklm_py": MagicMock()})
def test_notebooklm_upload_exception_logged(tmp_path):
    import sys

    fake_module = sys.modules["notebooklm_py"]
    fake_module.NotebookLMClient.side_effect = RuntimeError("auth failed")

    # Should not raise
    notebooklm.upload_to_notebooklm("nb-id", tmp_path / "file.md")


# --- integrations/obsidian ---

@patch("convmd.integrations.obsidian.webbrowser.open")
def test_open_in_obsidian(mock_open, tmp_path):
    obsidian.open_in_obsidian(tmp_path / "MyVault")
    mock_open.assert_called_once()
    args, _ = mock_open.call_args
    assert args[0].startswith("obsidian://open?vault=")
    assert "MyVault" in args[0]


@patch("convmd.integrations.obsidian.webbrowser.open", side_effect=RuntimeError("boom"))
def test_open_in_obsidian_handles_error(_mock_open, tmp_path):
    # Should not propagate
    obsidian.open_in_obsidian(tmp_path / "MyVault")


# --- exporters/pandoc_exporter ---

def test_pandoc_exporter_no_paths(tmp_path):
    assert PandocExporter("epub").export([], tmp_path) is None


@patch("convmd.exporters.pandoc_exporter.shutil.which", return_value=None)
def test_pandoc_exporter_no_pandoc(_mock_which, tmp_path):
    md = tmp_path / "a.md"
    md.write_text("# Hello", encoding="utf-8")
    assert PandocExporter("epub").export([md], tmp_path) is None


@patch("convmd.exporters.pandoc_exporter.subprocess.run")
@patch("convmd.exporters.pandoc_exporter.shutil.which", return_value="/usr/bin/pandoc")
def test_pandoc_exporter_success(_mock_which, mock_run, tmp_path):
    md = tmp_path / "a.md"
    md.write_text("# Hello", encoding="utf-8")
    out = PandocExporter("epub").export([md], tmp_path)
    assert out is not None
    assert out.name == "export.epub"
    mock_run.assert_called_once()


@patch("convmd.exporters.pandoc_exporter.subprocess.run",
       side_effect=subprocess.CalledProcessError(1, "pandoc", stderr="bad"))
@patch("convmd.exporters.pandoc_exporter.shutil.which", return_value="/usr/bin/pandoc")
def test_pandoc_exporter_pandoc_failure(_mock_which, _mock_run, tmp_path):
    md = tmp_path / "a.md"
    md.write_text("# Hello", encoding="utf-8")
    assert PandocExporter("epub").export([md], tmp_path) is None


@patch("convmd.exporters.pandoc_exporter.subprocess.run")
@patch("convmd.exporters.pandoc_exporter.shutil.which", return_value="/usr/bin/pandoc")
def test_pandoc_exporter_pdf_adds_xelatex(_mock_which, mock_run, tmp_path):
    md = tmp_path / "a.md"
    md.write_text("# Hello", encoding="utf-8")
    PandocExporter("pdf").export([md], tmp_path)
    args, _ = mock_run.call_args
    cmd = args[0]
    assert "--pdf-engine=xelatex" in cmd


def test_get_exporter_dispatch():
    assert get_exporter("md") is None
    assert get_exporter("json") is not None
    assert get_exporter("epub") is not None
    assert get_exporter("pdf") is not None
    assert get_exporter("unknown") is None


def test_export_files_md_is_noop(tmp_path):
    assert export_files("md", [tmp_path / "a.md"], tmp_path) is None
