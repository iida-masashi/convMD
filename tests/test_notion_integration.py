from unittest.mock import MagicMock, patch

import httpx

from convmd.core.utils import generate_frontmatter
from convmd.integrations.notion import export_to_notion

_SCHEMA_WITH_EXTRAS = {
    "properties": {
        "Name": {"type": "title"},
        "Source": {"type": "url"},
        "Tags": {"type": "multi_select"},
    }
}

_SCHEMA_TITLE_ONLY = {
    "properties": {
        "Name": {"type": "title"},
    }
}


def _make_file(tmp_path, title="My Title", source="https://example.com/a", tags=None, extra_body=""):
    file_path = tmp_path / "test.md"
    content = generate_frontmatter(title, source, tags=tags) + "Paragraph one.\n\nParagraph two." + extra_body
    file_path.write_text(content, encoding="utf-8")
    return file_path


def _mock_client(schema, create_status=200, create_json=None):
    """Build a MagicMock standing in for the httpx.Client context manager."""
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False

    schema_resp = MagicMock()
    schema_resp.raise_for_status.return_value = None
    schema_resp.json.return_value = schema

    create_resp = MagicMock()
    create_resp.raise_for_status.return_value = None
    create_resp.json.return_value = create_json or {"id": "page-123"}

    client.get.return_value = schema_resp
    client.post.return_value = create_resp

    patch_resp = MagicMock()
    patch_resp.raise_for_status.return_value = None
    client.patch.return_value = patch_resp

    return client


@patch("convmd.integrations.notion.get_client")
def test_export_success_with_source_and_tags(mock_get_client, tmp_path):
    client = _mock_client(_SCHEMA_WITH_EXTRAS)
    mock_get_client.return_value = client

    file_path = _make_file(tmp_path, tags=["python", "ai"])
    success = export_to_notion(file_path, "secret-token", "db-123")

    assert success is True
    client.get.assert_called_once()
    assert "db-123" in client.get.call_args[0][0]
    assert client.get.call_args[1]["headers"]["Authorization"] == "Bearer secret-token"
    assert client.get.call_args[1]["headers"]["Notion-Version"] == "2022-06-28"

    client.post.assert_called_once()
    import json as jsonlib

    payload = jsonlib.loads(client.post.call_args[1]["content"])
    assert payload["parent"] == {"database_id": "db-123"}
    assert payload["properties"]["Name"]["title"][0]["text"]["content"] == "My Title"
    assert payload["properties"]["Source"]["url"] == "https://example.com/a"
    assert payload["properties"]["Tags"]["multi_select"] == [{"name": "python"}, {"name": "ai"}]
    assert len(payload["children"]) == 2
    assert payload["children"][0]["type"] == "paragraph"
    assert payload["children"][0]["paragraph"]["rich_text"][0]["text"]["content"] == "Paragraph one."


@patch("convmd.integrations.notion.get_client")
def test_export_skips_missing_source_and_tags_properties(mock_get_client, tmp_path):
    client = _mock_client(_SCHEMA_TITLE_ONLY)
    mock_get_client.return_value = client

    file_path = _make_file(tmp_path, tags=["python"])
    success = export_to_notion(file_path, "secret-token", "db-123")

    assert success is True
    import json as jsonlib

    payload = jsonlib.loads(client.post.call_args[1]["content"])
    assert "Source" not in payload["properties"]
    assert "Tags" not in payload["properties"]
    assert set(payload["properties"].keys()) == {"Name"}


@patch("convmd.integrations.notion.get_client")
def test_export_no_tags_no_source_omits_properties(mock_get_client, tmp_path):
    client = _mock_client(_SCHEMA_WITH_EXTRAS)
    mock_get_client.return_value = client

    file_path = _make_file(tmp_path, source="", tags=None)
    success = export_to_notion(file_path, "secret-token", "db-123")

    assert success is True
    import json as jsonlib

    payload = jsonlib.loads(client.post.call_args[1]["content"])
    assert "Source" not in payload["properties"]
    assert "Tags" not in payload["properties"]


@patch("convmd.integrations.notion.get_client")
def test_export_batches_more_than_100_paragraphs(mock_get_client, tmp_path):
    client = _mock_client(_SCHEMA_WITH_EXTRAS)
    mock_get_client.return_value = client

    body = "\n\n".join(f"Paragraph {i}" for i in range(150))
    file_path = tmp_path / "big.md"
    file_path.write_text(generate_frontmatter("Big", "https://x") + body, encoding="utf-8")

    success = export_to_notion(file_path, "secret-token", "db-123")

    assert success is True
    import json as jsonlib

    create_payload = jsonlib.loads(client.post.call_args[1]["content"])
    assert len(create_payload["children"]) == 100

    client.patch.assert_called_once()
    assert "page-123" in client.patch.call_args[0][0]
    patch_payload = jsonlib.loads(client.patch.call_args[1]["content"])
    assert len(patch_payload["children"]) == 50


@patch("convmd.integrations.notion.get_client")
def test_export_no_title_property_returns_false(mock_get_client, tmp_path):
    client = _mock_client({"properties": {"Source": {"type": "url"}}})
    mock_get_client.return_value = client

    file_path = _make_file(tmp_path)
    success = export_to_notion(file_path, "secret-token", "db-123")

    assert success is False
    client.post.assert_not_called()


@patch("convmd.integrations.notion.get_client")
def test_export_schema_401_returns_false(mock_get_client, tmp_path):
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False

    request = httpx.Request("GET", "https://api.notion.com/v1/databases/db-123")
    response = httpx.Response(401, request=request)
    client.get.side_effect = httpx.HTTPStatusError("Unauthorized", request=request, response=response)
    mock_get_client.return_value = client

    file_path = _make_file(tmp_path)
    success = export_to_notion(file_path, "bad-token", "db-123")

    assert success is False
    client.post.assert_not_called()


@patch("convmd.integrations.notion.get_client")
def test_export_database_404_returns_false(mock_get_client, tmp_path):
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False

    request = httpx.Request("GET", "https://api.notion.com/v1/databases/db-123")
    response = httpx.Response(404, request=request)
    client.get.side_effect = httpx.HTTPStatusError("Not Found", request=request, response=response)
    mock_get_client.return_value = client

    file_path = _make_file(tmp_path)
    success = export_to_notion(file_path, "secret-token", "missing-db")

    assert success is False


@patch("convmd.integrations.notion.get_client")
def test_export_network_error_returns_false(mock_get_client, tmp_path):
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    client.get.side_effect = httpx.ConnectError("connection failed")
    mock_get_client.return_value = client

    file_path = _make_file(tmp_path)
    success = export_to_notion(file_path, "secret-token", "db-123")

    assert success is False


def test_export_missing_file_returns_false(tmp_path):
    missing = tmp_path / "does_not_exist.md"
    assert export_to_notion(missing, "token", "db-123") is False


@patch("convmd.integrations.notion.get_client")
def test_export_logs_error_on_failure(mock_get_client, tmp_path, caplog):
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    client.get.side_effect = RuntimeError("boom")
    mock_get_client.return_value = client

    file_path = _make_file(tmp_path)
    with caplog.at_level("ERROR"):
        success = export_to_notion(file_path, "secret-token", "db-123")

    assert success is False
    assert any("Failed to export to Notion" in r.message for r in caplog.records)


@patch("convmd.integrations.notion.get_client")
def test_export_logs_success(mock_get_client, tmp_path, caplog):
    client = _mock_client(_SCHEMA_WITH_EXTRAS)
    mock_get_client.return_value = client

    file_path = _make_file(tmp_path)
    with caplog.at_level("INFO"):
        success = export_to_notion(file_path, "secret-token", "db-123")

    assert success is True
    assert any("Successfully exported" in r.message for r in caplog.records)
