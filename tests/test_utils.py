from unittest.mock import MagicMock, patch

from convmd.core.download import process_images
from convmd.core.utils import generate_frontmatter, sanitize_filename


def test_generate_frontmatter():
    title = "Test Title"
    url = "https://example.com"
    tags = ["tag1", "tag2"]
    frontmatter = generate_frontmatter(title, url, tags)

    assert f'title: "{title}"' in frontmatter
    assert f'source: "{url}"' in frontmatter
    assert 'tags:\n  - "tag1"\n  - "tag2"' in frontmatter
    assert "created_at:" in frontmatter


def test_generate_frontmatter_obsidian_style():
    # extra args contain a mix of types to test serialization
    frontmatter = generate_frontmatter(
        title="Test Title",
        url="https://example.com",
        tags=["a", "b"],
        author="John",
        extra={"aliases": ["Alt"], "custom_id": 123}
    )

    assert "---\n" in frontmatter
    assert 'title: "Test Title"' in frontmatter
    assert 'source: "https://example.com"' in frontmatter
    assert 'author: "John"' in frontmatter
    # Tags should be a YAML list
    assert 'tags:\n  - "a"\n  - "b"\n' in frontmatter
    assert 'aliases:\n  - "Alt"\n' in frontmatter
    assert 'custom_id: 123' in frontmatter
    assert 'created_at: ' in frontmatter # Should exist


@patch("convmd.core.download.httpx.Client")
def test_process_images_encoding(mock_client_class, tmp_path):
    # Mocking httpx.Client
    mock_response = MagicMock()
    mock_response.content = b"fake image data"

    mock_client_instance = MagicMock()
    mock_client_instance.get.return_value = mock_response
    mock_client_instance.__enter__.return_value = mock_client_instance

    mock_client_class.return_value = mock_client_instance

    output_dir = tmp_path
    md_content = "![alt](https://example.com/樫原神社１.jpg)"
    base_url = "https://example.com/"

    new_md = process_images(md_content, base_url, output_dir)

    # Check if link was replaced correctly
    assert "![alt](images/樫原神社１.jpg)" in new_md
    # Check if file exists
    assert (output_dir / "images" / "樫原神社１.jpg").exists()


@patch("convmd.core.download.httpx.Client")
def test_process_images_double_encoding(mock_client_class, tmp_path):
    mock_response = MagicMock()
    mock_response.content = b"fake image data"

    mock_client_instance = MagicMock()
    mock_client_instance.get.return_value = mock_response
    mock_client_instance.__enter__.return_value = mock_client_instance

    mock_client_class.return_value = mock_client_instance

    output_dir = tmp_path
    # URL is already encoded
    md_content = "![alt](https://example.com/%E5%A4%A7%E7%94%9F%E7%A5%9E%E7%A4%BE.jpg)"
    base_url = "https://example.com/"

    new_md = process_images(md_content, base_url, output_dir)

    # It should not be double encoded to %25E5...
    # The filename should be unquoted
    assert "![alt](images/大生神社.jpg)" in new_md
    assert (output_dir / "images" / "大生神社.jpg").exists()


def test_sanitize_filename():
    # 1. Basic sanitization of invalid characters
    assert sanitize_filename('test/file:name*with?"illegal"|chars<>') == "testfilenamewithillegalchars"

    # 2. Trim trailing dots and spaces (Windows protection)
    assert sanitize_filename("  my_file_name.  ") == "my_file_name"

    # 3. Fallback to 'Untitled' for empty or only-invalid characters
    assert sanitize_filename("") == "Untitled"
    assert sanitize_filename("   ") == "Untitled"
    assert sanitize_filename("///:::***") == "Untitled"

    # 4. Long ASCII string truncation at max_bytes (default 200)
    long_ascii = "a" * 300
    res_ascii = sanitize_filename(long_ascii)
    assert len(res_ascii.encode("utf-8")) <= 200
    assert len(res_ascii) == 200

    # 5. Long Japanese string truncation within max_bytes without broken multibyte chars
    long_jp = "森永製菓（2201）の財務情報ならログミーFinance 【QAあり】森永製菓、ROICマネジメントの実践による成長性と資本収益性の好循環で、飛躍的な成長軌道の確立を目指す - ログミーファイナンス"
    res_jp = sanitize_filename(long_jp)
    assert len(res_jp.encode("utf-8")) <= 200
    # Must be valid UTF-8 without decoding error
    res_jp.encode("utf-8").decode("utf-8")
    assert not res_jp.endswith(" ")
    assert not res_jp.endswith(".")
