"""Tests for the retry-with-backoff behavior in core/http.py."""

from unittest.mock import MagicMock, patch

import httpx

from convmd.core.http import download_binary, get_html, get_json


def _status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.com/x")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(f"status {status_code}", request=request, response=response)


def _make_client_sequence(side_effects):
    """Build a mock get_client() context manager whose .get() raises/returns per call."""
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.side_effect = side_effects
    return mock_client


@patch("convmd.core.http.random.uniform", return_value=0.0)
@patch("convmd.core.http.time.sleep")
@patch("convmd.core.http.get_client")
def test_get_json_retries_then_succeeds(mock_get_client, mock_sleep, _mock_jitter):
    ok_response = MagicMock()
    ok_response.raise_for_status = MagicMock()
    ok_response.json.return_value = {"ok": True}

    mock_get_client.return_value = _make_client_sequence(
        [httpx.ConnectTimeout("timeout"), httpx.ConnectTimeout("timeout"), ok_response]
    )

    result = get_json("https://example.com/x")

    assert result == {"ok": True}
    assert mock_sleep.call_count == 2
    delays = [call.args[0] for call in mock_sleep.call_args_list]
    assert delays == [0.5, 1.0]


@patch("convmd.core.http.random.uniform", return_value=0.0)
@patch("convmd.core.http.time.sleep")
@patch("convmd.core.http.get_client")
def test_get_json_retries_on_5xx_then_succeeds(mock_get_client, mock_sleep, _mock_jitter):
    ok_response = MagicMock()
    ok_response.raise_for_status = MagicMock()
    ok_response.json.return_value = {"ok": True}

    bad_response = MagicMock()
    bad_response.raise_for_status.side_effect = _status_error(503)

    mock_get_client.return_value = _make_client_sequence([bad_response, ok_response])

    result = get_json("https://example.com/x")

    assert result == {"ok": True}
    assert mock_sleep.call_count == 1
    assert mock_sleep.call_args_list[0].args[0] == 0.5


@patch("convmd.core.http.random.uniform", return_value=0.0)
@patch("convmd.core.http.time.sleep")
@patch("convmd.core.http.get_client")
def test_get_json_retries_on_429_then_succeeds(mock_get_client, mock_sleep, _mock_jitter):
    ok_response = MagicMock()
    ok_response.raise_for_status = MagicMock()
    ok_response.json.return_value = {"ok": True}

    bad_response = MagicMock()
    bad_response.raise_for_status.side_effect = _status_error(429)

    mock_get_client.return_value = _make_client_sequence([bad_response, ok_response])

    result = get_json("https://example.com/x")

    assert result == {"ok": True}
    assert mock_sleep.call_count == 1


@patch("convmd.core.http.time.sleep")
@patch("convmd.core.http.get_client")
def test_get_json_404_does_not_retry(mock_get_client, mock_sleep):
    bad_response = MagicMock()
    bad_response.raise_for_status.side_effect = _status_error(404)

    mock_get_client.return_value = _make_client_sequence([bad_response])

    result = get_json("https://example.com/x")

    assert result is None
    mock_sleep.assert_not_called()
    assert mock_get_client.return_value.get.call_count == 1


@patch("convmd.core.http.random.uniform", return_value=0.0)
@patch("convmd.core.http.time.sleep")
@patch("convmd.core.http.get_client")
def test_get_json_exhausts_retries_returns_none(mock_get_client, mock_sleep, _mock_jitter):
    mock_get_client.return_value = _make_client_sequence(
        [
            httpx.ConnectTimeout("timeout"),
            httpx.ConnectTimeout("timeout"),
            httpx.ConnectTimeout("timeout"),
            httpx.ConnectTimeout("timeout"),
        ]
    )

    result = get_json("https://example.com/x", max_retries=3, base_delay=0.5)

    assert result is None
    assert mock_sleep.call_count == 3
    assert mock_get_client.return_value.get.call_count == 4


@patch("convmd.core.http.random.uniform", return_value=0.0)
@patch("convmd.core.http.time.sleep")
@patch("convmd.core.http.get_client")
def test_get_html_retries_then_succeeds(mock_get_client, mock_sleep, _mock_jitter):
    ok_response = MagicMock()
    ok_response.raise_for_status = MagicMock()
    ok_response.headers = {"content-type": "text/html; charset=utf-8"}
    ok_response.content = ("<html><body><p>" + "hello world " * 100 + "</p></body></html>").encode(
        "utf-8"
    )

    mock_get_client.return_value = _make_client_sequence(
        [httpx.TimeoutException("timeout"), ok_response]
    )

    result = get_html("https://example.com/x")

    assert result is not None
    assert "hello world" in result
    assert mock_sleep.call_count == 1


@patch("convmd.core.http.time.sleep")
@patch("convmd.core.http.get_client")
def test_get_html_404_does_not_retry(mock_get_client, mock_sleep):
    bad_response = MagicMock()
    bad_response.raise_for_status.side_effect = _status_error(404)

    mock_get_client.return_value = _make_client_sequence([bad_response])

    result = get_html("https://example.com/x")

    assert result is None
    mock_sleep.assert_not_called()
    assert mock_get_client.return_value.get.call_count == 1


@patch("convmd.core.http.random.uniform", return_value=0.0)
@patch("convmd.core.http.time.sleep")
@patch("convmd.core.http.get_client")
def test_download_binary_retries_then_succeeds(mock_get_client, mock_sleep, _mock_jitter, tmp_path):
    ok_response = MagicMock()
    ok_response.raise_for_status = MagicMock()
    ok_response.iter_bytes.return_value = [b"chunk1", b"chunk2"]
    ok_stream_cm = MagicMock()
    ok_stream_cm.__enter__.return_value = ok_response

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.stream.side_effect = [
        httpx.ConnectError("refused"),
        ok_stream_cm,
    ]
    mock_get_client.return_value = mock_client

    dest = tmp_path / "out.bin"
    result = download_binary("https://example.com/x", dest)

    assert result is True
    assert dest.read_bytes() == b"chunk1chunk2"
    assert mock_sleep.call_count == 1


@patch("convmd.core.http.time.sleep")
@patch("convmd.core.http.get_client")
def test_download_binary_404_does_not_retry(mock_get_client, mock_sleep, tmp_path):
    bad_response = MagicMock()
    bad_response.raise_for_status.side_effect = _status_error(404)
    bad_stream_cm = MagicMock()
    bad_stream_cm.__enter__.return_value = bad_response

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.stream.return_value = bad_stream_cm
    mock_get_client.return_value = mock_client

    dest = tmp_path / "out.bin"
    result = download_binary("https://example.com/x", dest)

    assert result is False
    mock_sleep.assert_not_called()
    assert mock_client.stream.call_count == 1


@patch("convmd.core.http.random.uniform", return_value=0.0)
@patch("convmd.core.http.time.sleep")
@patch("convmd.core.http.get_client")
def test_download_binary_exhausts_retries_returns_false(
    mock_get_client, mock_sleep, _mock_jitter, tmp_path
):
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.stream.side_effect = httpx.ConnectError("refused")
    mock_get_client.return_value = mock_client

    dest = tmp_path / "out.bin"
    result = download_binary("https://example.com/x", dest, max_retries=2, base_delay=0.1)

    assert result is False
    assert mock_sleep.call_count == 2
    assert mock_client.stream.call_count == 3
