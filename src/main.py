"""
main.py — Orchestrates the full AI News Digest pipeline.

Steps:
  1. Load environment variables (from .env for local dev, from shell/CI for prod)
  2. Fetch AI news from all sources
  3. Rank and summarise the top 7 stories with the LLM
  4. Build the HTML email
  5. Send the email via Gmail SMTP
"""

import logging
import sys
from datetime import datetime, timezone

# Load .env file if present (no-op in CI where vars are injected directly)
from dotenv import load_dotenv

load_dotenv()

from fetcher import fetch_all_items        # noqa: E402
from ranker import rank_and_summarize      # noqa: E402
from formatter import build_email_html     # noqa: E402
from sender import send_email              # noqa: E402

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    # ------------------------------------------------------------------
    # 1. Date string used in subject and email body
    # ------------------------------------------------------------------
    today = datetime.now(tz=timezone.utc)
    today_date = today.strftime("%B %d, %Y")          # e.g. "April 28, 2026"
    today_full = today.strftime("%A, %B %d, %Y")      # e.g. "Monday, April 28, 2026"
    today_iso = today.strftime("%Y-%m-%d")            # e.g. "2026-04-28" — used for Supabase

    logger.info("=== AI News Digest — %s ===", today_date)

    # ------------------------------------------------------------------
    # 2. Fetch news
    # ------------------------------------------------------------------
    logger.info("Step 1/4 · Fetching news from all sources…")
    try:
        items = fetch_all_items()
    except Exception as exc:
        logger.error("Fatal error during fetch: %s", exc)
        sys.exit(1)

    logger.info("Fetched %d items in total.", len(items))

    if not items:
        logger.error(
            "No items fetched from any source. "
            "Check network connectivity and source availability."
        )
        sys.exit(1)

    # ------------------------------------------------------------------
    # 3. Rank & summarise
    # ------------------------------------------------------------------
    logger.info("Step 2/4 · Ranking and summarising with LLM…")
    try:
        ranked_items = rank_and_summarize(items)
    except Exception as exc:
        logger.error("Fatal error during ranking: %s", exc)
        sys.exit(1)

    logger.info("Top 7 stories selected:")
    for story in ranked_items:
        logger.info(
            "  #%s (%.1f) %s",
            story.get("rank", "?"),
            float(story.get("score", 0)),
            story.get("title", ""),
        )

    # ------------------------------------------------------------------
    # 4. Build HTML email
    # ------------------------------------------------------------------
    logger.info("Step 3/4 · Building HTML email…")
    try:
        html_body = build_email_html(ranked_items, today_full)
    except Exception as exc:
        logger.error("Fatal error during HTML generation: %s", exc)
        sys.exit(1)

    subject = f"Your AI Digest — {today_date} · 7 stories"
    logger.info("Subject: %s", subject)

    # ------------------------------------------------------------------
    # 5. Send email
    # ------------------------------------------------------------------
    logger.info("Step 4/4 · Sending email via Gmail SMTP…")
    try:
        send_email(html_body, subject)
    except EnvironmentError as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.error("Fatal error while sending email: %s", exc)
        sys.exit(1)

    print("Digest sent successfully.")

    # ------------------------------------------------------------------
    # 6. Send Telegram notification (immediately after email)
    # ------------------------------------------------------------------
    try:
        from notifier import send_telegram_notification
        send_telegram_notification()
    except Exception as exc:
        logger.error("Step 6 failed — could not send Telegram notification: %s", exc)

    # ------------------------------------------------------------------
    # 7. Save digest to Supabase
    # ------------------------------------------------------------------
    try:
        from storage import save_digest
        save_digest(ranked_items, today_iso)
    except Exception as exc:
        logger.error("Step 7 failed — could not save digest to Supabase: %s", exc)

    logger.info("=== Pipeline complete ===")


if __name__ == "__main__":
    main()
