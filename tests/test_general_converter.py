from unittest.mock import MagicMock, patch

from convmd.core.download import fetch_html


@patch("convmd.core.http.httpx.Client")
def test_fetch_html_encoding(mock_client_class):
    # Mock get_client to return our client instance
    mock_response = MagicMock()
    mock_response.encoding = "utf-8"
    mock_response.charset_encoding = "utf-8"
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

