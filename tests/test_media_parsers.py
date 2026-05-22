"""Smoke tests for media parsers — mock the HTTP/external boundary and verify Markdown shape."""

from unittest.mock import MagicMock, patch

from convmd.parsers.media import (
    audio,
    hatena,
    medium,
    podcast,
    qiita,
    speakerdeck,
    substack,
    wikipedia,
    zenn,
)

# --- Qiita ---

@patch("convmd.parsers.media.qiita.process_images", side_effect=lambda body, *_a, **_k: body)
@patch("convmd.parsers.media.qiita.get_json")
def test_qiita_article(mock_get_json, _mock_imgs, tmp_path):
    mock_get_json.return_value = {
        "title": "Hello Qiita",
        "url": "https://qiita.com/u/items/abc123",
        "body": "# Hi\n\ncontent body",
        "tags": [{"name": "python"}, {"name": "test"}],
    }
    out = qiita.convert_qiita("https://qiita.com/u/items/abc123", tmp_path)
    assert out is not None
    text = out.read_text(encoding="utf-8")
    assert "content body" in text
    assert 'title: "Hello Qiita"' in text
    assert '- "qiita"' in text
    assert '- "python"' in text


@patch("convmd.parsers.media.qiita.process_images", side_effect=lambda body, *_a, **_k: body)
@patch("convmd.parsers.media.qiita.get_json")
def test_qiita_user_listing(mock_get_json, _mock_imgs, tmp_path):
    # get_json receives the full URL (fetch_qiita_api prepends the host),
    # so match on substring rather than startswith.
    def side(full_url):
        if "items?query=user:" in full_url:
            return [{"id": "abc"}]
        return {
            "title": "Article",
            "url": "https://qiita.com/u/items/abc",
            "body": "body",
            "tags": [],
        }

    mock_get_json.side_effect = side
    out = qiita.convert_qiita("https://qiita.com/someuser", tmp_path)
    assert out is not None
    assert out.is_dir()
    assert any(out.iterdir())


def test_qiita_unrecognized_url_returns_none(tmp_path):
    assert qiita.convert_qiita("https://qiita.com/", tmp_path) is None


# --- Zenn ---

@patch("convmd.parsers.media.zenn.process_images", side_effect=lambda body, *_a, **_k: body)
@patch("convmd.parsers.media.zenn.get_json")
def test_zenn_article(mock_get_json, _mock_imgs, tmp_path):
    mock_get_json.return_value = {
        "article": {
            "title": "Zenn Article",
            "body_markdown": "## Section\n\nbody",
            "topics": [{"name": "python"}],
        }
    }
    out = zenn.convert_zenn("https://zenn.dev/user/articles/myslug", tmp_path)
    assert out is not None
    text = out.read_text(encoding="utf-8")
    assert "## Section" in text
    assert '- "zenn"' in text


def test_zenn_non_article_url(tmp_path):
    assert zenn.convert_zenn("https://zenn.dev/user", tmp_path) is None


@patch("convmd.parsers.media.zenn.process_images", side_effect=lambda body, *_a, **_k: body)
@patch("convmd.parsers.media.zenn.get_json", return_value=None)
def test_zenn_api_failure(_mock_get, _mock_imgs, tmp_path):
    assert zenn.convert_zenn("https://zenn.dev/user/articles/slug", tmp_path) is None


# --- Wikipedia ---

@patch("convmd.parsers.media.wikipedia.process_images", side_effect=lambda body, *_a, **_k: body)
@patch("convmd.parsers.media.wikipedia.get_html")
def test_wikipedia_article(mock_get_html, _mock_imgs, tmp_path):
    mock_get_html.return_value = "<html><body><p>Some content.</p></body></html>"
    out = wikipedia.convert_wikipedia("https://ja.wikipedia.org/wiki/Test", tmp_path)
    assert out is not None
    text = out.read_text(encoding="utf-8")
    assert "Some content." in text
    assert '- "wikipedia"' in text
    assert '- "ja"' in text


def test_wikipedia_invalid_url(tmp_path):
    assert wikipedia.convert_wikipedia("https://ja.wikipedia.org/", tmp_path) is None


@patch("convmd.parsers.media.wikipedia.get_html", return_value=None)
def test_wikipedia_fetch_failure(_mock_get, tmp_path):
    assert wikipedia.convert_wikipedia("https://ja.wikipedia.org/wiki/Test", tmp_path) is None


# --- Hatena ---

@patch("convmd.parsers.media.hatena.process_images", side_effect=lambda body, *_a, **_k: body)
@patch("convmd.parsers.media.hatena.get_html")
def test_hatena(mock_get_html, _mock_imgs, tmp_path):
    mock_get_html.return_value = """
    <html><head><title>Blog Post</title></head>
    <body><div class="entry-content"><p>Post body.</p></div></body></html>
    """
    out = hatena.convert_hatena("https://x.hatenablog.com/entry/1", tmp_path)
    assert out is not None
    text = out.read_text(encoding="utf-8")
    assert "Post body." in text
    assert '- "hatena"' in text


@patch("convmd.parsers.media.hatena.get_html", return_value=None)
def test_hatena_no_html(_mock_get, tmp_path):
    assert hatena.convert_hatena("https://x.hatenablog.com/entry/1", tmp_path) is None


@patch("convmd.parsers.media.hatena.get_html",
       return_value="<html><head><title>X</title></head><body><div>nada</div></body></html>")
def test_hatena_no_entry_body(_mock_get, tmp_path):
    assert hatena.convert_hatena("https://x.hatenablog.com/entry/1", tmp_path) is None


# --- Substack ---

@patch("convmd.parsers.media.substack.process_images", side_effect=lambda body, *_a, **_k: body)
@patch("convmd.parsers.media.substack.get_html")
def test_substack(mock_get_html, _mock_imgs, tmp_path):
    mock_get_html.return_value = (
        "<html><head><title>Substack Title</title></head>"
        "<body><article><h1>Substack Title</h1><p>Newsletter body content here.</p></article></body></html>"
    )
    out = substack.convert_substack("https://foo.substack.com/p/hello", tmp_path)
    assert out is not None
    text = out.read_text(encoding="utf-8")
    assert "Newsletter body content" in text
    assert '- "substack"' in text


@patch("convmd.parsers.media.substack.get_html", return_value=None)
def test_substack_no_html(_mock_get, tmp_path):
    assert substack.convert_substack("https://foo.substack.com/p/hello", tmp_path) is None


# --- Medium ---

@patch("convmd.parsers.media.medium.process_images", side_effect=lambda body, *_a, **_k: body)
@patch("convmd.parsers.media.medium.get_html")
def test_medium(mock_get_html, _mock_imgs, tmp_path):
    mock_get_html.return_value = (
        "<html><head><title>Medium Title</title></head>"
        "<body><article><h1>Medium Title</h1><p>This is the Medium article body content.</p></article></body></html>"
    )
    out = medium.convert_medium("https://medium.com/@user/article-slug", tmp_path)
    assert out is not None
    text = out.read_text(encoding="utf-8")
    assert "Medium article body content" in text
    assert '- "medium"' in text


# --- Audio ---

def test_audio_missing_file(tmp_path):
    assert audio.convert_audio_file(tmp_path / "nope.mp3", tmp_path) is None


def test_audio_format_timestamp():
    assert audio.format_timestamp(65) == "01:05"
    assert audio.format_timestamp(3725) == "1:02:05"


@patch("faster_whisper.WhisperModel")
def test_audio_transcribe_success(mock_model_class, tmp_path):
    fake_segments = [
        MagicMock(start=0.0, text="hello world"),
        MagicMock(start=2.5, text="second line"),
    ]
    info = MagicMock(language="en", language_probability=0.99)
    mock_inst = MagicMock()
    mock_inst.transcribe.return_value = (iter(fake_segments), info)
    mock_model_class.return_value = mock_inst

    src = tmp_path / "test.mp3"
    src.write_bytes(b"\x00")

    out = audio.convert_audio_file(src, tmp_path)
    assert out is not None
    text = out.read_text(encoding="utf-8")
    assert "hello world" in text
    assert "second line" in text
    assert '- "audio_transcript"' in text


# --- Podcast ---

def test_podcast_is_rss_detection():
    assert podcast._is_rss('<?xml version="1.0"?><rss>') is True
    assert podcast._is_rss('<html><body>') is False


def test_podcast_episode_entries_extracts_enclosures():
    rss = """<?xml version="1.0"?>
    <rss><channel>
      <item><title>Ep1</title><enclosure url="https://x/ep1.mp3" /></item>
      <item><title>Ep2</title><enclosure url="https://x/ep2.mp3" /></item>
    </channel></rss>
    """
    entries = podcast._episode_entries(rss, limit=10)
    assert len(entries) == 2
    assert entries[0] == ("Ep1", "https://x/ep1.mp3")


def test_podcast_episode_entries_parse_error_returns_empty():
    assert podcast._episode_entries("<not xml", limit=5) == []


@patch("convmd.parsers.media.podcast.get_html", return_value=None)
def test_podcast_no_feed(_mock_get, tmp_path):
    assert podcast.convert_podcast("https://x/rss", tmp_path) is None


@patch("convmd.parsers.media.podcast.get_html", return_value="<html>not rss</html>")
def test_podcast_not_an_rss(_mock_get, tmp_path):
    assert podcast.convert_podcast("https://x/feed", tmp_path) is None


# --- NDL ---

def test_ndl_no_pid(tmp_path):
    # convert_ndl returns None implicitly when PID cannot be parsed
    assert ndl_safe_call("https://dl.ndl.go.jp/", tmp_path) is None


def ndl_safe_call(url, tmp_path):
    from convmd.parsers.media import ndl

    return ndl.convert_ndl(url, tmp_path)


@patch("convmd.parsers.media.ndl.process_iiif_manifest")
@patch("convmd.parsers.media.ndl.httpx.get")
def test_ndl_success(mock_get, mock_iiif, tmp_path):
    resp = MagicMock(status_code=200)
    resp.json.return_value = {
        "label": "NDL Test Title",
        "metadata": [
            {"label": "著者", "value": "山田太郎"},
            {"label": "出版年月日", "value": "1900"},
        ],
    }
    resp.raise_for_status = MagicMock()
    mock_get.return_value = resp
    mock_iiif.return_value = "![[images/p_0001.jpg]]"

    from convmd.parsers.media import ndl

    ndl.convert_ndl("https://dl.ndl.go.jp/pid/1234567", tmp_path)

    # image_dir is not created (process_iiif_manifest is mocked), so md is at top level
    md_path = tmp_path / "NDL Test Title.md"
    assert md_path.exists()
    text = md_path.read_text(encoding="utf-8")
    assert "山田太郎" in text
    assert "1900" in text


@patch("convmd.parsers.media.ndl.httpx.get")
def test_ndl_manifest_404(mock_get, tmp_path):
    resp = MagicMock(status_code=404)
    mock_get.return_value = resp
    from convmd.parsers.media import ndl

    ndl.convert_ndl("https://dl.ndl.go.jp/pid/0000000", tmp_path)
    # Should not raise and should not create any md file
    assert list(tmp_path.glob("*.md")) == []


# --- SpeakerDeck ---

def test_speakerdeck_slide_image_extraction():
    html = """
    <html><body>
      <img data-src="https://files.speakerdeck.com/presentations/abc/slide_0.jpg">
      <img src="https://example.com/unrelated.png">
      <img data-src="https://files.speakerdeck.com/presentations/abc/slide_1.jpg">
    </body></html>
    """
    urls = speakerdeck._slide_image_urls(html)
    assert len(urls) == 2
    assert all("slide_" in u for u in urls)


def test_speakerdeck_og_image_fallback():
    html = '<html><head><meta property="og:image" content="https://x/og.png"></head></html>'
    urls = speakerdeck._slide_image_urls(html)
    assert urls == ["https://x/og.png"]


@patch("convmd.parsers.media.speakerdeck.gemini.is_configured", return_value=False)
@patch("convmd.parsers.media.speakerdeck.download_image")
@patch("convmd.parsers.media.speakerdeck.get_html")
def test_speakerdeck_pipeline(mock_get_html, mock_dl, _mock_cfg, tmp_path):
    mock_get_html.return_value = """
    <html><head><title>My Deck</title></head><body>
      <img data-src="https://files.speakerdeck.com/p/abc/slide_0.jpg">
    </body></html>
    """
    out = speakerdeck.convert_speakerdeck("https://speakerdeck.com/u/d", tmp_path)
    assert out is not None
    assert out.exists()
    mock_dl.assert_called_once()
    text = out.read_text(encoding="utf-8")
    assert "## Slide 1" in text


@patch("convmd.parsers.media.speakerdeck.get_html", return_value=None)
def test_speakerdeck_no_html(_mock_get, tmp_path):
    assert speakerdeck.convert_speakerdeck("https://speakerdeck.com/u/d", tmp_path) is None


@patch(
    "convmd.parsers.media.speakerdeck.get_html",
    return_value="<html><head><title>X</title></head><body></body></html>",
)
def test_speakerdeck_no_slides(_mock_get, tmp_path):
    assert speakerdeck.convert_speakerdeck("https://speakerdeck.com/u/d", tmp_path) is None
