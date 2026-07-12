import os
from unittest.mock import patch

from convmd.core.http import _resolve_charset, _verify_default, encode_url_path, get_html_with_js


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


def test_get_html_with_js_falls_back_to_browser4_when_playwright_missing():
    with patch("convmd.core.http._get_html_with_browser4_fallback", return_value="<html>b4</html>") as fallback:
        with patch.dict("sys.modules", {"playwright": None, "playwright.sync_api": None}):
            html = get_html_with_js("https://example.com")
    assert html == "<html>b4</html>"
    fallback.assert_called_once()


def test_get_html_with_js_falls_back_to_browser4_when_playwright_raises():
    class _FakeSyncPlaywright:
        def __enter__(self):
            raise RuntimeError("boom")

        def __exit__(self, *exc):
            return False

    with patch("playwright.sync_api.sync_playwright", return_value=_FakeSyncPlaywright()), patch(
        "convmd.core.http._get_html_with_browser4_fallback", return_value="<html>b4</html>"
    ) as fallback:
        html = get_html_with_js("https://example.com")
    assert html == "<html>b4</html>"
    fallback.assert_called_once()


def test_browser4_fallback_returns_none_when_cli_missing():
    from convmd.core.http import _get_html_with_browser4_fallback

    with patch("convmd.core.browser4.is_available", return_value=False):
        assert _get_html_with_browser4_fallback("https://example.com", timeout=10) is None
