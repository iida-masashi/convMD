import pytest
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from convmd.core.utils import generate_frontmatter
from convmd.core.download import process_images

def test_generate_frontmatter():
    title = "Test Title"
    url = "https://example.com"
    tags = ["tag1", "tag2"]
    frontmatter = generate_frontmatter(title, url, tags)
    
    assert f"title: \"{title}\"" in frontmatter
    assert f"source: \"{url}\"" in frontmatter
    assert "tags: [tag1, tag2]" in frontmatter
    assert "date:" in frontmatter

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
