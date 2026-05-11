from unittest.mock import MagicMock, patch

from convmd.integrations.slack import send_to_slack


@patch("convmd.integrations.slack.httpx.Client")
def test_send_to_slack_success(mock_client_class):
    mock_client_instance = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client_instance

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_client_instance.post.return_value = mock_response

    send_to_slack("http://slack.webhook.example.com", "Hello World")

    mock_client_instance.post.assert_called_once_with(
        "http://slack.webhook.example.com", json={"text": "Hello World"}
    )


@patch("convmd.integrations.slack.httpx.Client")
def test_send_to_slack_empty_url(mock_client_class):
    send_to_slack("", "Hello World")
    mock_client_class.assert_not_called()
