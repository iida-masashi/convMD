"""Routing tests — patch at module level to bypass closure binding in routing._build_routes."""

from unittest.mock import patch

import convmd.routing as routing
from convmd.cli_args import RunConfig


def _cfg(tmp_path):
    return RunConfig(target="x", output_dir=tmp_path)


def setup_function(_func):
    # Reset cache between tests so patched handlers take effect.
    routing._routes_cache = None


def teardown_function(_func):
    routing._routes_cache = None


def test_route_for_github(tmp_path):
    with patch("convmd.parsers.sns.github.convert_github") as m:
        routing.dispatch_url("https://github.com/x/y", tmp_path, _cfg(tmp_path))
    m.assert_called_once()


def test_route_for_youtube(tmp_path):
    with patch("convmd.parsers.sns.youtube.convert_youtube") as m:
        routing.dispatch_url(
            "https://www.youtube.com/watch?v=abcdefghijk", tmp_path, _cfg(tmp_path)
        )
    m.assert_called_once()


def test_route_for_kokusho_passes_bilingual(tmp_path):
    cfg = RunConfig(target="x", output_dir=tmp_path, bilingual=True)
    with patch("convmd.parsers.media.kokusho.convert_kokusho") as m:
        routing.dispatch_url("https://kokusho.nijl.ac.jp/biblio/1/", tmp_path, cfg)
    assert m.called
    assert m.call_args.kwargs.get("bilingual") is True


def test_route_fallback(tmp_path):
    with patch("convmd.parsers.general.convert_general_website") as m:
        routing.dispatch_url("https://example.com/article", tmp_path, _cfg(tmp_path))
    m.assert_called_once()


def test_routes_buildable():
    routes = routing._build_routes()
    assert len(routes) > 5
