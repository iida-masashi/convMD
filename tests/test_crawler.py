from unittest.mock import MagicMock, patch

from convmd.core.crawler import crawl_urls


@patch("convmd.core.crawler.httpx.Client")
def test_crawl_urls_depth_0(mock_client):
    urls = crawl_urls("http://example.com/start", 0)
    assert urls == ["http://example.com/start"]
    mock_client.assert_not_called()


@patch("convmd.core.crawler.httpx.Client")
def test_crawl_urls_depth_1(mock_client_class):
    mock_client_instance = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client_instance

    # Mock response for the start URL
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "text/html"}
    mock_response.content = b"""
    <html>
        <body>
            <a href="/page1">Page 1</a>
            <a href="http://example.com/page2">Page 2</a>
            <a href="http://external.com/page3">External</a>
            <a href="#section">Anchor</a>
        </body>
    </html>
    """
    mock_client_instance.get.return_value = mock_response

    urls = crawl_urls("http://example.com/start", 1)

    # Should contain start URL, relative URL resolved, and absolute same-domain URL
    # Should exclude external domain and fragment-only links (which resolve to start_url)
    assert "http://example.com/start" in urls
    assert "http://example.com/page1" in urls
    assert "http://example.com/page2" in urls
    assert "http://external.com/page3" not in urls

    # Depth 1 means we don't crawl the children of page1 and page2
    assert mock_client_instance.get.call_count == 1
