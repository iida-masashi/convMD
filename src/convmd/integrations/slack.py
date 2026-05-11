"""Slack webhook integration."""

from __future__ import annotations

import logging

import httpx

from convmd.constants import DEFAULT_TIMEOUT
from convmd.core.http import _verify_default

logger = logging.getLogger(__name__)


def send_to_slack(webhook_url: str, text: str) -> None:
    """POST a plain-text message to a Slack incoming webhook."""
    if not webhook_url:
        return

    logger.info("Sending message to Slack...")
    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT, verify=_verify_default()) as client:
            response = client.post(webhook_url, json={"text": text})
            response.raise_for_status()
        logger.info("Successfully sent message to Slack.")
    except Exception as e:
        logger.error(f"Failed to send message to Slack: {e}")
