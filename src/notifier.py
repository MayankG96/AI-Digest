"""
notifier.py — Sends a Telegram notification summarising the top 3 digest stories.
Failure is non-fatal: the email was already sent before this is called.
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)


def send_telegram_notification() -> None:
    """
    Sends a short Telegram message notifying the user their digest is ready.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.warning(
            "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — skipping notification."
        )
        return

    message = "Good morning. Your AI digest is in your inbox. Send me a voice note if something's worth posting about."

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("Telegram notification sent successfully.")
    except Exception as exc:
        logger.error("Failed to send Telegram notification: %s", exc)
