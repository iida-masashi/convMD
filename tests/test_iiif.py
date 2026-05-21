from unittest.mock import MagicMock, patch

from convmd.core.iiif import process_iiif_manifest


@patch("convmd.core.iiif.httpx.get")
@patch("convmd.core.iiif.download_image")
@patch("convmd.core.iiif.transcribe_image_with_gemini")
@patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"})
def test_process_iiif_manifest_success(mock_transcribe, mock_download, mock_get, tmp_path):
    # Setup mock HTTP response for manifest
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "sequences": [
            {"canvases": [{"images": [{"resource": {"@id": "http://example.com/img1.jpg"}}]}]}
        ]
    }
    mock_get.return_value = mock_response

    # Setup mock OCR
    mock_transcribe.return_value = "Mocked OCR text"

    image_dir = tmp_path / "images"
    manifest_url = "http://example.com/manifest.json"

    markdown_result = process_iiif_manifest(manifest_url, image_dir)

    assert "![[images/page_0001.jpg]]" in markdown_result
    assert "> Mocked OCR text" in markdown_result

    mock_get.assert_called_once_with(manifest_url, timeout=60.0)
    mock_download.assert_called_once_with(
        "http://example.com/img1.jpg", image_dir / "page_0001.jpg"
    )
    mock_transcribe.assert_called_once()


@patch("convmd.core.iiif.httpx.get")
def test_process_iiif_manifest_http_error(mock_get, tmp_path):
    # Setup mock HTTP exception
    mock_get.side_effect = Exception("Network Error")

    image_dir = tmp_path / "images"
    manifest_url = "http://example.com/manifest.json"

    markdown_result = process_iiif_manifest(manifest_url, image_dir)

    assert markdown_result == ""
