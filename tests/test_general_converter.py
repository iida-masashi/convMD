import pytest
import urllib.parse
from general_converter import fetch_url

def test_fetch_url_encoding(mocker):
    # Mock urllib.request.urlopen
    mock_response = mocker.MagicMock()
    mock_response.headers.get_content_charset.return_value = "utf-8"
    mock_response.read.return_value = b"<html><body>Test</body></html>"
    mock_response.__enter__.return_value = mock_response
    
    mock_urlopen = mocker.patch("urllib.request.urlopen", return_value=mock_response)
    mock_request = mocker.patch("urllib.request.Request")
    
    # Test with a URL that has Japanese characters (already encoded)
    url = "https://ja.wikipedia.org/wiki/%E5%A4%A7%E7%94%9F%E7%A5%9E%E7%A4%BE"
    fetch_url(url)
    
    # Check what URL was actually requested
    args, kwargs = mock_request.call_args
    requested_url = args[0]
    
    # It should NOT be double encoded. 
    # %E5 (E) should remain %E5, not become %25E5
    assert "%25E5" not in requested_url
    assert "%E5%A4%A7%E7%94%9F%E7%A5%9E%E7%A4%BE" in requested_url
