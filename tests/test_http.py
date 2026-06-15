import os
from unittest.mock import patch

from convmd.core.http import _resolve_charset, _verify_default, encode_url_path


def test_encode_url_path_idempotent():
    url = "https://ja.wikipedia.org/wiki/%E5%A4%A7%E7%94%9F%E7%A5%9E%E7%A4%BE"
    out = encode_url_path(url)
    assert "%25E5" not in out
    assert "%E5%A4%A7" in out


def test_encode_url_path_handles_unicode():
    url = "https://example.com/樫原神社1.jpg"
    out = encode_url_path(url)
    assert "%E6" in out


def test_verify_default_true_by_default():
    with patch.dict(os.environ, {}, clear=True):
        assert _verify_default() is True


def test_verify_default_disabled_via_env():
    with patch.dict(os.environ, {"CONVMD_INSECURE_SSL": "1"}, clear=True):
        assert _verify_default() is False


def test_resolve_charset_prefers_header():
    assert _resolve_charset("text/html; charset=Shift_JIS", b"<meta charset=utf-8>") == "Shift_JIS"


def test_resolve_charset_falls_back_to_meta():
    body = b'<meta http-equiv="Content-Type" content="text/html; charset=ISO-2022-JP" />'
    assert _resolve_charset("text/html", body) == "ISO-2022-JP"


def test_resolve_charset_meta_short_form():
    assert _resolve_charset("text/html", b'<meta charset="euc-jp">') == "euc-jp"


def test_resolve_charset_defaults_to_utf8():
    assert _resolve_charset("text/html", b"<html><body>hi</body></html>") == "utf-8"
