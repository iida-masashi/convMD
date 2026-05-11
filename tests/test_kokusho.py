from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from convmd.parsers.media.kokusho import convert_kokusho


@patch("convmd.parsers.media.kokusho.httpx.get")
@patch("convmd.parsers.media.kokusho.process_iiif_manifest")
@patch("builtins.open", new_callable=mock_open)
def test_convert_kokusho_success(mock_file_open, mock_process_iiif, mock_get, tmp_path):
    # Setup mock for detail API
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "hshomeipdf": "Test Title",
        "author": ["Test Author"],
        "bpublish": ["Edo Period"],
        "satsu": "1",
        "collection": "Test Collection",
        "chuki": ["Note 1"],
    }
    mock_get.return_value = mock_response

    # Setup mock for IIIF processing
    mock_process_iiif.return_value = "![[images/page_0001.jpg]]"

    url = "https://kokusho.nijl.ac.jp/biblio/12345/"
    output_dir = tmp_path

    # Execute
    convert_kokusho(url, output_dir)

    # Assertions
    mock_get.assert_called_once_with(
        "https://kokusho.nijl.ac.jp/api/biblioDetail/12345", timeout=10.0
    )
    mock_process_iiif.assert_called_once()

    mock_file_open.assert_called_once()

    # Check what was written to the file
    written_content = "".join(
        call.args[0] for call in mock_file_open.return_value.write.call_args_list
    )
    assert 'title: "Test Title"' in written_content
    assert 'author: "Test Author"' in written_content
    assert 'biblio_id: "12345"' in written_content
    assert "## 注記" in written_content
    assert "- Note 1" in written_content
    assert "## 画像" in written_content
    assert "![[images/page_0001.jpg]]" in written_content


def test_convert_kokusho_invalid_url():
    # Should exit early and log error without raising
    url = "https://kokusho.nijl.ac.jp/invalid/12345/"
    convert_kokusho(url, Path("/tmp"))
