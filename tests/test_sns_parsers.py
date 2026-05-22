"""Smoke tests for note.com and twitter/X parsers."""

import json
from unittest.mock import MagicMock, patch

from convmd.parsers.sns import note, twitter

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


# --- twitter (X) ---

def _next_data(entries):
    payload = {"props": {"pageProps": {"timeline": {"entries": entries}}}}
    inner = json.dumps(payload)
    return f'<html><body><script id="__NEXT_DATA__" type="application/json">{inner}</script></body></html>'


@patch("convmd.parsers.sns.twitter.get_client")
def test_twitter_timeline(mock_get_client, tmp_path):
    entries = [
        {
            "type": "tweet",
            "content": {
                "tweet": {
                    "id_str": "111",
                    "created_at": "2026-05-01T00:00:00Z",
                    "text": "Hello tweet body http://t.co/foo",
                    "entities": {
                        "media": [
                            {"media_url_https": "https://x.com/img.jpg", "url": "http://t.co/foo"}
                        ]
                    },
                },
            },
        }
    ]
    mock_response = MagicMock()
    mock_response.text = _next_data(entries)
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_get_client.return_value = mock_client

    out = twitter.convert_twitter("someuser", tmp_path)
    assert out is not None
    text = out.read_text(encoding="utf-8")
    assert "Hello tweet body" in text
    assert "https://x.com/img.jpg" in text
    assert "111" in text
    # t.co URL should be stripped from text
    assert "t.co/foo" not in text.split("![image]")[0]


@patch("convmd.parsers.sns.twitter.get_client")
def test_twitter_no_next_data(mock_get_client, tmp_path):
    mock_response = MagicMock()
    mock_response.text = "<html><body>no next data here</body></html>"
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_get_client.return_value = mock_client

    assert twitter.convert_twitter("u", tmp_path) is None


@patch("convmd.parsers.sns.twitter.get_client")
def test_twitter_no_tweets(mock_get_client, tmp_path):
    mock_response = MagicMock()
    mock_response.text = _next_data([])
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_get_client.return_value = mock_client

    assert twitter.convert_twitter("u", tmp_path) is None


@patch("convmd.parsers.sns.twitter.get_client", side_effect=Exception("network"))
def test_twitter_network_error(_mock_client, tmp_path):
    assert twitter.convert_twitter("u", tmp_path) is None
