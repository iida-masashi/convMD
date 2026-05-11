from convmd.core import cache


def test_record_and_retrieve(tmp_path):
    cache.record(
        tmp_path,
        "https://example.com",
        body="hello",
        output_path=tmp_path / "x.md",
        etag='"abc"',
        last_modified="Mon, 01 Jan 2024 00:00:00 GMT",
    )
    etag, lm = cache.get_validators(tmp_path, "https://example.com")
    assert etag == '"abc"'
    assert lm == "Mon, 01 Jan 2024 00:00:00 GMT"

    h, body = cache.get_previous(tmp_path, "https://example.com")
    assert body == "hello"
    assert h == cache.hash_text("hello")


def test_diff(tmp_path):
    assert cache.diff("a\nb", "a\nb", url="u") is None
    out = cache.diff("a\nb\nc", "a\nB\nc", url="u")
    assert out is not None
    assert "-b" in out and "+B" in out


def test_get_validators_missing(tmp_path):
    assert cache.get_validators(tmp_path, "missing") == (None, None)
    assert cache.get_previous(tmp_path, "missing") == (None, None)
