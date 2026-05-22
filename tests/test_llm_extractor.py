from unittest.mock import MagicMock, patch

from convmd.core.llm_extractor import extract_with_llm


@patch("convmd.core.gemini.get_client")
def test_extract_with_llm_success(mock_get_client, tmp_path):
    # Setup mock Gemini client
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Setup mock response
    mock_response = MagicMock()
    mock_response.text = (
        '{"title": "Test Article", "author": "Alice", "date": "2026-05-21", '
        '"content_markdown": "This is a test content.", "tags": ["test", "ai"]}'
    )
    mock_client.models.generate_content.return_value = mock_response

    output_dir = tmp_path
    html = "<html><body><h1>Test</h1><p>Content</p></body></html>"

    result_path = extract_with_llm(html, output_dir, url="http://test.com")

    assert result_path is not None
    assert result_path.name == "Test Article.md"
    content = result_path.read_text(encoding="utf-8")
    assert 'title: "Test Article"' in content
    assert 'author: "Alice"' in content
    assert "This is a test content." in content
    assert "ai_extract" in content


@patch("convmd.core.gemini.get_client")
def test_extract_with_llm_failure(mock_get_client, tmp_path):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Simulate error
    mock_client.models.generate_content.side_effect = Exception("API Error")

    result = extract_with_llm("<html></html>", tmp_path)
    assert result is None
