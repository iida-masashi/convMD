import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from convmd.core.ocr import transcribe_image_with_gemini

@patch("convmd.core.ocr.genai.Client")
@patch("PIL.Image.open")
def test_transcribe_image_with_gemini_success(mock_image_open, mock_genai_client, tmp_path):
    # Setup mocks
    mock_client_instance = MagicMock()
    mock_genai_client.return_value = mock_client_instance
    mock_response = MagicMock()
    mock_response.text = "Mocked OCR text"
    mock_client_instance.models.generate_content.return_value = mock_response
    
    # Create a dummy image file
    img_path = tmp_path / "test.jpg"
    img_path.touch()

    # Set fake API key
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        result = transcribe_image_with_gemini(img_path)

    assert result == "Mocked OCR text"
    mock_image_open.assert_called_once_with(img_path)
    mock_client_instance.models.generate_content.assert_called_once()

@patch("convmd.core.ocr.genai.Client")
def test_transcribe_image_with_gemini_no_api_key(mock_genai_client, tmp_path):
    img_path = tmp_path / "test.jpg"
    img_path.touch()

    # Ensure no API key is set
    with patch.dict(os.environ, {}, clear=True):
        result = transcribe_image_with_gemini(img_path)

    assert result == ""
    mock_genai_client.assert_not_called()

@patch("convmd.core.ocr.genai.Client")
@patch("PIL.Image.open")
def test_transcribe_image_with_gemini_exception(mock_image_open, mock_genai_client, tmp_path):
    mock_client_instance = MagicMock()
    mock_genai_client.return_value = mock_client_instance
    mock_client_instance.models.generate_content.side_effect = Exception("API Error")
    
    img_path = tmp_path / "test.jpg"
    img_path.touch()

    with patch.dict(os.environ, {"GOOGLE_API_KEY": "fake_key"}):
        result = transcribe_image_with_gemini(img_path)

    assert result == ""
