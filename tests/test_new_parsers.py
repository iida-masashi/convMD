"""Smoke tests for Phase 2 parsers — mock out HTTP and verify Markdown output shape."""

from unittest.mock import patch

from convmd.parsers.sns import github, hackernews, reddit


@patch("convmd.parsers.sns.github.get_json")
def test_github_readme(mock_get_json, tmp_path):
    import base64

    encoded = base64.b64encode(b"# Hello World\n").decode()
    mock_get_json.return_value = {"content": encoded}
    out = github.convert_github("https://github.com/foo/bar", tmp_path)
    assert out is not None
    text = out.read_text(encoding="utf-8")
    assert "Hello World" in text
    assert "tags: [github, readme]" in text


@patch("convmd.parsers.sns.github.get_json")
def test_github_issue(mock_get_json, tmp_path):
    def side(endpoint):
        if endpoint.endswith("/comments"):
            return [{"user": {"login": "alice"}, "created_at": "2026-01-01", "body": "looks good"}]
        return {
            "title": "Bug",
            "body": "Something is broken.",
            "html_url": "https://github.com/foo/bar/issues/1",
        }

    mock_get_json.side_effect = lambda ep, headers=None: side(ep)
    out = github.convert_github("https://github.com/foo/bar/issues/1", tmp_path)
    assert out is not None
    text = out.read_text(encoding="utf-8")
    assert "Something is broken." in text
    assert "alice" in text


@patch("convmd.parsers.sns.reddit.get_json")
def test_reddit(mock_get_json, tmp_path):
    mock_get_json.return_value = [
        {
            "data": {
                "children": [
                    {
                        "data": {
                            "title": "Hello",
                            "selftext": "body text",
                            "permalink": "/r/test/comments/abc/hello/",
                            "author": "u1",
                        }
                    }
                ]
            }
        },
        {
            "data": {
                "children": [
                    {"kind": "t1", "data": {"author": "alice", "body": "nice", "score": 5}}
                ]
            }
        },
    ]
    out = reddit.convert_reddit("https://www.reddit.com/r/test/comments/abc/hello/", tmp_path)
    assert out is not None
    text = out.read_text(encoding="utf-8")
    assert "Hello" in text
    assert "alice" in text


@patch("convmd.parsers.sns.hackernews._fetch_item")
def test_hackernews(mock_fetch, tmp_path):
    def fake(item_id):
        if item_id == 1:
            return {"title": "Story", "by": "alice", "score": 100, "kids": [2]}
        if item_id == 2:
            return {"by": "bob", "text": "<p>nice point</p>"}
        return None

    mock_fetch.side_effect = fake
    out = hackernews.convert_hackernews("https://news.ycombinator.com/item?id=1", tmp_path)
    assert out is not None
    text = out.read_text(encoding="utf-8")
    assert "Story" in text
    assert "nice point" in text
