import os
from unittest.mock import MagicMock, patch

from convmd.core.transform import (
    apply_obsidian_links,
    generate_executive_summary,
    transform_markdown_with_gemini,
)


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


@patch("convmd.core.transform.genai.Client")
def test_apply_obsidian_links(mock_genai_client, tmp_path):
    mock_client_instance = MagicMock()
    mock_genai_client.return_value = mock_client_instance
    mock_response = MagicMock()
    mock_response.text = "Test with [[Link]] and #Tag"
    mock_client_instance.models.generate_content.return_value = mock_response

    md_path = tmp_path / "test.md"
    md_path.write_text("Test", encoding="utf-8")

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake"}):
        res_path = apply_obsidian_links(md_path)

    assert res_path is not None
    assert res_path.name == "test_linked.md"
    assert res_path.read_text(encoding="utf-8").strip() == "Test with [[Link]] and #Tag"


@patch("convmd.core.transform.genai.Client")
def test_generate_executive_summary(mock_genai_client, tmp_path):
    mock_client_instance = MagicMock()
    mock_genai_client.return_value = mock_client_instance
    mock_response = MagicMock()
    mock_response.text = "# Executive Summary\nAll good."
    mock_client_instance.models.generate_content.return_value = mock_response

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake"}):
        res_path = generate_executive_summary("Lots of text here.", tmp_path)

    assert res_path is not None
    assert res_path.name == "executive_summary.md"
    assert res_path.read_text(encoding="utf-8").strip() == "# Executive Summary\nAll good."
