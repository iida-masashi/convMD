import logging

import httpx

logger = logging.getLogger(__name__)


def send_to_slack(webhook_url: str, text: str) -> None:
    """
    指定されたSlackのWebhook URLにテキストメッセージを送信する。
    """
    if not webhook_url:
        return

    logger.info("Sending message to Slack...")
    try:
        # Construct Slack webhook payload
        payload = {"text": text}

        with httpx.Client(timeout=10.0, verify=False) as client:
            response = client.post(webhook_url, json=payload)
            response.raise_for_status()

        logger.info("Successfully sent message to Slack.")
    except Exception as e:
        logger.error(f"Failed to send message to Slack: {e}")
