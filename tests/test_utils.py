import pytest
import os
import urllib.parse
from utils import generate_frontmatter, process_images

def test_generate_frontmatter():
    title = "Test Title"
    url = "https://example.com"
    tags = ["tag1", "tag2"]
    frontmatter = generate_frontmatter(title, url, tags)
    
    assert f"title: \"{title}\"" in frontmatter
    assert f"source: \"{url}\"" in frontmatter
    assert "tags: [tag1, tag2]" in frontmatter
    assert "date:" in frontmatter

def test_process_images_encoding(tmp_path, mocker):
    # Mocking urllib.request.urlopen and Request
    mock_response = mocker.MagicMock()
    mock_response.read.return_value = b"fake image data"
    mock_response.__enter__.return_value = mock_response
    mocker.patch("urllib.request.urlopen", return_value=mock_response)
    mocker.patch("urllib.request.Request")
    
    # Mocking os.path.exists to always return False for first check, then True after "download"
    # Actually, simpler to just let it "download" to a temp dir
    output_dir = str(tmp_path)
    md_content = "![alt](https://example.com/樫原神社１.jpg)"
    base_url = "https://example.com/"
    
    new_md = process_images(md_content, base_url, output_dir)
    
    # Check if link was replaced correctly
    assert "![alt](images/樫原神社１.jpg)" in new_md
    # Check if file exists
    assert os.path.exists(os.path.join(output_dir, "images", "樫原神社１.jpg"))

def test_process_images_double_encoding(tmp_path, mocker):
    mock_response = mocker.MagicMock()
    mock_response.read.return_value = b"fake image data"
    mock_response.__enter__.return_value = mock_response
    mocker.patch("urllib.request.urlopen", return_value=mock_response)
    
    output_dir = str(tmp_path)
    # URL is already encoded
    md_content = "![alt](https://example.com/%E5%A4%A7%E7%94%9F%E7%A5%9E%E7%A4%BE.jpg)"
    base_url = "https://example.com/"
    
    new_md = process_images(md_content, base_url, output_dir)
    
    # It should not be double encoded to %25E5...
    # The filename should be unquoted
    assert "![alt](images/大生神社.jpg)" in new_md
    assert os.path.exists(os.path.join(output_dir, "images", "大生神社.jpg"))
