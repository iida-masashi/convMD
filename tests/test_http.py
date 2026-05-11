import os
from unittest.mock import patch

from convmd.core.http import _verify_default, encode_url_path


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
