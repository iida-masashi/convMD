import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from convmd.core.transform import transform_markdown_with_gemini

@patch("convmd.core.transform.genai.Client")
def test_transform_markdown_success(mock_genai_client, tmp_path):
    # Setup mocks
    mock_client_instance = MagicMock()
    mock_genai_client.return_value = mock_client_instance
    mock_response = MagicMock()
    mock_response.text = "```markdown\n# Transformed Text\n```"
    mock_client_instance.models.generate_content.return_value = mock_response
    
    # Create a dummy markdown file
    md_path = tmp_path / "test.md"
    md_path.write_text("# Original Text", encoding="utf-8")

    # Set fake API key
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        transform_markdown_with_gemini(md_path, "Translate this")

    # Verify that transformed file is created
    transformed_path = tmp_path / "test_transformed.md"
    assert transformed_path.exists()
    assert transformed_path.read_text(encoding="utf-8").strip() == "# Transformed Text"
    
    mock_client_instance.models.generate_content.assert_called_once()

@patch("convmd.core.transform.genai.Client")
def test_transform_markdown_no_api_key(mock_genai_client, tmp_path):
    md_path = tmp_path / "test.md"
    md_path.write_text("# Original Text", encoding="utf-8")

    # Ensure no API key is set
    with patch.dict(os.environ, {}, clear=True):
        transform_markdown_with_gemini(md_path, "Translate this")

    transformed_path = tmp_path / "test_transformed.md"
    assert not transformed_path.exists()
    mock_genai_client.assert_not_called()
