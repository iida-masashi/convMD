import os
from unittest.mock import MagicMock, patch

from convmd.core.transform import (
    apply_obsidian_links,
    generate_executive_summary,
    transform_markdown_with_gemini,
)


@patch("convmd.core.gemini.genai.Client")
def test_transform_markdown_success(mock_genai_client, tmp_path):
    mock_client_instance = MagicMock()
    mock_genai_client.return_value = mock_client_instance
    mock_response = MagicMock()
    mock_response.text = "```markdown\n# Transformed Text\n```"
    mock_client_instance.models.generate_content.return_value = mock_response

    md_path = tmp_path / "test.md"
    md_path.write_text("# Original Text", encoding="utf-8")

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        transform_markdown_with_gemini(md_path, "Translate this")

    transformed_path = tmp_path / "test_transformed.md"
    assert transformed_path.exists()
    assert transformed_path.read_text(encoding="utf-8").strip() == "# Transformed Text"
    mock_client_instance.models.generate_content.assert_called_once()


@patch("convmd.core.gemini.genai.Client")
def test_transform_markdown_no_api_key(mock_genai_client, tmp_path):
    md_path = tmp_path / "test.md"
    md_path.write_text("# Original Text", encoding="utf-8")

    with patch.dict(os.environ, {}, clear=True):
        transform_markdown_with_gemini(md_path, "Translate this")

    transformed_path = tmp_path / "test_transformed.md"
    assert not transformed_path.exists()
    mock_genai_client.assert_not_called()


@patch("convmd.core.transform.gemini.is_configured", return_value=True)
@patch("convmd.core.transform.gemini.generate_text")
def test_apply_obsidian_links(mock_generate, mock_config, tmp_path):
    # Setup test file
    test_file = tmp_path / "test.md"
    test_file.write_text("---\ntitle: \"Test\"\ntags:\n  - \"raw\"\n---\n\n徳島県は阿波国と呼ばれていた。", encoding="utf-8")
    
    # Mock AI response with tags at the end
    mock_generate.return_value = "---\ntitle: \"Test\"\ntags:\n  - \"raw\"\n---\n\n[[徳島県]]は[[阿波国]]と呼ばれていた。\n\nTAGS: 徳島, 歴史"
    
    out_path = apply_obsidian_links(test_file)
    
    assert out_path is not None
    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8")
    
    # Check if tags were injected into frontmatter
    assert 'tags:\n  - "raw"\n  - "徳島"\n  - "歴史"' in content
    # Check if text was linked
    assert "[[徳島県]]は[[阿波国]]" in content
    # Check if TAGS marker was removed from body
    assert "TAGS:" not in content


@patch("convmd.core.gemini.genai.Client")
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
