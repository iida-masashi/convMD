"""Smoke tests for note.com and X (via Grok) parsers."""

from unittest.mock import MagicMock, patch

from convmd.parsers.sns import grok, note

# --- note.com ---

@patch("convmd.parsers.sns.note.get_json")
def test_note_creator_listing(mock_get_json, tmp_path):
    listing = {
        "data": {
            "contents": [
                {"key": "k1", "name": "First Note", "publishAt": "2026-01-15T00:00:00+09:00"},
            ],
            "isLastPage": True,
        }
    }
    detail = {"data": {"body": "<h1>Hi</h1><p>note body</p>"}}

    def side(full_url):
        if "/contents?" in full_url:
            return listing
        if "/notes/" in full_url:
            return detail
        return None

    mock_get_json.side_effect = side
    out = note.convert_note_com("someuser", tmp_path)
    assert out is not None
    assert out.is_dir()
    files = list(out.glob("*.md"))
    assert len(files) == 1
    text = files[0].read_text(encoding="utf-8")
    assert "note body" in text
    assert '- "note"' in text
    assert files[0].name.startswith("2026-01-15-")


@patch("convmd.parsers.sns.note.get_json", return_value=None)
def test_note_no_data_returns_none(_mock_get, tmp_path):
    assert note.convert_note_com("nouser", tmp_path) is None


@patch("convmd.parsers.sns.note.get_json")
def test_note_empty_contents(mock_get_json, tmp_path):
    mock_get_json.return_value = {"data": {"contents": [], "isLastPage": True}}
    assert note.convert_note_com("nouser", tmp_path) is None


# --- grok (X via xAI Agent Tools) ---

def _grok_response(text):
    return {
        "output": [{"type": "message", "content": [{"text": text}]}],
        "usage": {"cost_in_usd_ticks": 150000000},
    }


@patch.dict("os.environ", {"XAI_API_KEY": "test-key"})
@patch("convmd.parsers.sns.grok.get_client")
def test_grok_posts(mock_get_client, tmp_path):
    mock_response = MagicMock()
    mock_response.json.return_value = _grok_response(
        "**投稿日時**: Wed, 03 Jun 2026 02:31:30 GMT  \n"
        "**本文**: 弧帯文の原型を勉強中です。  \n"
        "**投稿URL**: https://x.com/u/status/111"
    )
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_get_client.return_value = mock_client

    out = grok.convert_grok("u", tmp_path)
    assert out is not None
    text = out.read_text(encoding="utf-8")
    assert "弧帯文の原型を勉強中です" in text
    assert "evidence_type: \"ai_mediated\"" in text
    assert "要検証" in text
    # raw JSON anchor is persisted alongside the MD
    assert (tmp_path / "u_grok_raw.json").exists()


@patch.dict("os.environ", {}, clear=True)
def test_grok_no_key(tmp_path):
    assert grok.convert_grok("u", tmp_path) is None


@patch.dict("os.environ", {"XAI_API_KEY": "test-key"})
@patch("convmd.parsers.sns.grok.get_client")
def test_grok_empty_output(mock_get_client, tmp_path):
    mock_response = MagicMock()
    mock_response.json.return_value = _grok_response("")
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_get_client.return_value = mock_client

    assert grok.convert_grok("u", tmp_path) is None
