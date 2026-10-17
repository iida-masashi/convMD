from unittest.mock import MagicMock, patch

from convmd.core.download import fetch_html


@patch("convmd.core.http.httpx.Client")
def test_fetch_html_encoding(mock_client_class):
    # Mock get_client to return our client instance
    mock_response = MagicMock()
    mock_response.encoding = "utf-8"
    mock_response.charset_encoding = "utf-8"
    mock_response.headers = {"content-type": "text/html; charset=utf-8"}
    mock_response.content = b"<html><body>Test" + b" padding" * 200 + b"</body></html>"

    mock_client_instance = MagicMock()
    mock_client_instance.get.return_value = mock_response
    mock_client_instance.__enter__.return_value = mock_client_instance

    mock_client_class.return_value = mock_client_instance

    # Test with a URL that has Japanese characters (already encoded)
    url = "https://ja.wikipedia.org/wiki/%E5%A4%A7%E7%94%9F%E7%A5%9E%E7%A4%BE"
    html = fetch_html(url)

    assert html == "<html><body>Test" + " padding" * 200 + "</body></html>"

    # Check what URL was actually requested
    args, kwargs = mock_client_instance.get.call_args
    requested_url = args[0]

    # It should NOT be double encoded.
    assert "%25E5" not in requested_url
    assert "%E5%A4%A7%E7%94%9F%E7%A5%9E%E7%A4%BE" in requested_url
    assert kwargs["headers"]["Accept"].startswith("text/markdown")


@patch("convmd.core.http.get_html_with_js")
@patch("convmd.core.http.httpx.Client")
def test_fetch_html_skips_spa_detection_for_markdown_response(mock_client_class, mock_js):
    mock_response = MagicMock()
    mock_response.headers = {"content-type": "text/markdown; charset=utf-8"}
    # Short markdown (< 1000 chars) should NOT trigger SPA Playwright fallback
    mock_response.content = b"# Cloudflare Markdown\n\nShort direct markdown content."

    mock_client_instance = MagicMock()
    mock_client_instance.get.return_value = mock_response
    mock_client_instance.__enter__.return_value = mock_client_instance
    mock_client_class.return_value = mock_client_instance

    result = fetch_html("https://example.com/doc")
    assert result == "# Cloudflare Markdown\n\nShort direct markdown content."
    mock_js.assert_not_called()


@patch("convmd.parsers.general.fetch_html")
def test_convert_general_website_direct_markdown(mock_fetch, tmp_path):
    from convmd.parsers.general import convert_general_website

    mock_fetch.return_value = (
        "# Direct Server Markdown\n\n" + "This is direct markdown content from the edge. " * 5
    )
    out = convert_general_website("https://example.com/edge", tmp_path)
    assert out is not None
    text = out.read_text(encoding="utf-8")
    assert 'title: "Direct Server Markdown"' in text
    assert "This is direct markdown content from the edge." in text


@patch("convmd.parsers.general.fetch_html")
def test_convert_general_website_uses_trafilatura_and_metadata(mock_fetch, tmp_path):
    from convmd.parsers.general import convert_general_website

    article_body = "Trafilatura extracted main article paragraph with rich detail. " * 6
    html = f"""<!DOCTYPE html>
    <html>
      <head>
        <title>Test Article Title</title>
        <meta name="author" content="Jane Doe">
        <meta name="date" content="2026-10-01">
      </head>
      <body>
        <article>
          <h1>Test Article Title</h1>
          <p>{article_body}</p>
        </article>
      </body>
    </html>"""
    mock_fetch.return_value = html

    out = convert_general_website("https://example.com/article", tmp_path)
    assert out is not None
    text = out.read_text(encoding="utf-8")
    assert 'title: "Test Article Title"' in text
    assert 'author: "Jane Doe"' in text
    assert 'published_at: "2026-10-01"' in text
    assert "Trafilatura extracted main article paragraph" in text


@patch("convmd.parsers.general._extract_with_trafilatura", return_value=(None, None, None, None))
@patch("convmd.parsers.general.fetch_html")
def test_convert_general_website_falls_back_to_readability(mock_fetch, _mock_traf, tmp_path):
    from convmd.parsers.general import convert_general_website

    body_text = "Readability fallback body content with enough length to pass check. " * 5
    mock_fetch.return_value = (
        f"<html><head><title>Fallback Page</title></head>"
        f"<body><article><p>{body_text}</p></article></body></html>"
    )
    out = convert_general_website("https://example.com/fallback", tmp_path)
    assert out is not None
    text = out.read_text(encoding="utf-8")
    assert 'title: "Fallback Page"' in text
    assert "Readability fallback body content" in text

