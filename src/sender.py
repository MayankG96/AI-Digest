"""
sender.py — Sends the HTML digest via Gmail SMTP with STARTTLS.
Reads credentials from environment variables; never hardcodes secrets.
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 587


def send_email(html_body: str, subject: str) -> None:
    """
    Send an HTML email via Gmail SMTP (STARTTLS).

    Required environment variables:
        GMAIL_ADDRESS      — the Gmail address used to authenticate and send
        GMAIL_APP_PASSWORD — a 16-character Gmail App Password (not your account password)
        RECIPIENT_EMAIL    — the address the digest is delivered to

    Args:
        html_body: Complete HTML string for the email body.
        subject:   Email subject line.

    Raises:
        EnvironmentError: If any required env var is missing.
        smtplib.SMTPException: On SMTP authentication or send failure,
                               with the SMTP error code in the message.
        RuntimeError: On any other unexpected failure.
    """
    # ------------------------------------------------------------------ #
    # Read credentials
    # ------------------------------------------------------------------ #
    gmail_address = os.environ.get("GMAIL_ADDRESS")
    gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD")
    recipient_email = os.environ.get("RECIPIENT_EMAIL")

    missing = [
        name
        for name, val in (
            ("GMAIL_ADDRESS", gmail_address),
            ("GMAIL_APP_PASSWORD", gmail_app_password),
            ("RECIPIENT_EMAIL", recipient_email),
        )
        if not val
    ]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variable(s): {', '.join(missing)}"
        )

    # ------------------------------------------------------------------ #
    # Build MIME message
    # ------------------------------------------------------------------ #
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = recipient_email

    # Attach HTML part (plain-text fallback omitted intentionally — digest
    # is visual-first; add a MIMEText("plain") part here if desired)
    html_part = MIMEText(html_body, "html", "utf-8")
    msg.attach(html_part)

    # ------------------------------------------------------------------ #
    # Connect and send
    # ------------------------------------------------------------------ #
    logger.info("Connecting to %s:%d …", _SMTP_HOST, _SMTP_PORT)
    try:
        with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()

            try:
                server.login(gmail_address, gmail_app_password)
            except smtplib.SMTPAuthenticationError as exc:
                raise smtplib.SMTPAuthenticationError(
                    exc.smtp_code,
                    f"Gmail authentication failed (code {exc.smtp_code}). "
                    "Ensure GMAIL_APP_PASSWORD is a valid App Password, not your "
                    "account password. See README for setup instructions.",
                ) from exc

            try:
                server.sendmail(gmail_address, recipient_email, msg.as_string())
            except smtplib.SMTPRecipientsRefused as exc:
                raise smtplib.SMTPRecipientsRefused(
                    {
                        recipient_email: (
                            list(exc.recipients.values())[0]
                            if exc.recipients
                            else (550, b"Recipient refused")
                        )
                    }
                ) from exc
            except smtplib.SMTPException as exc:
                code = getattr(exc, "smtp_code", "?")
                raise smtplib.SMTPException(
                    f"SMTP error while sending (code {code}): {exc}"
                ) from exc

    except smtplib.SMTPConnectError as exc:
        raise smtplib.SMTPConnectError(
            exc.smtp_code,
            f"Could not connect to {_SMTP_HOST}:{_SMTP_PORT} "
            f"(code {exc.smtp_code}). Check network access.",
        ) from exc

    logger.info("Email sent successfully to %s.", recipient_email)
