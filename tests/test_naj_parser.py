from unittest.mock import patch

from convmd.parsers.media.naj import convert_naj


@patch("convmd.parsers.media.naj.process_iiif_manifest")
def test_convert_naj_success(mock_process_iiif, tmp_path):
    mock_process_iiif.return_value = "![[images/page_0001.jpg]]"

    url = "https://www.digital.archives.go.jp/img/1207985#1"
    output_dir = tmp_path

    res_path = convert_naj(url, output_dir, ocr=True)

    assert res_path is not None
    assert res_path.name == "NAJ_1207985.md"
    content = res_path.read_text(encoding="utf-8")
    assert "naj" in content
    assert "iiif" in content
    assert "# NAJ_1207985" in content
    assert "![[images/page_0001.jpg]]" in content

    mock_process_iiif.assert_called_once()
    # Check if ocr_prompt was passed
    args, kwargs = mock_process_iiif.call_args
    assert "ocr_prompt" in kwargs
    assert "和古書や漢籍" in kwargs["ocr_prompt"]
