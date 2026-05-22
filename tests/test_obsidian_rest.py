from unittest.mock import MagicMock, patch

from convmd.integrations.obsidian_rest import export_to_obsidian_api


@patch("convmd.integrations.obsidian_rest.httpx.Client.put")
def test_export_to_obsidian_api_success(mock_put, tmp_path):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_put.return_value = mock_response

    file_path = tmp_path / "test.md"
    file_path.write_text("content", encoding="utf-8")

    success = export_to_obsidian_api(file_path, "https://127.0.0.1:27124", "secret-token", "Inbox")

    assert success is True
    mock_put.assert_called_once()
    args, kwargs = mock_put.call_args
    assert "https://127.0.0.1:27124/vault/Inbox/test.md" in args[0]
    assert kwargs["headers"]["Authorization"] == "Bearer secret-token"
    assert kwargs["headers"]["Content-Type"] == "text/markdown"
    assert kwargs["content"] == b"content"
