"""
storage.py — Saves ranked digest items to Supabase digest_items table.
Upserts on (date, rank) so re-runs are always safe.
"""

import logging
import os

from supabase import create_client

logger = logging.getLogger(__name__)


def save_digest(items: list, date: str) -> None:
    """
    Upserts 7 ranked digest items into Supabase digest_items table.

    Args:
        items: List of ranked dicts with keys: rank, title, url, summary,
               why_it_matters, score, source.
        date:  ISO date string, e.g. "2026-05-09".

    Raises:
        RuntimeError: If the upsert fails.
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY must be set to save the digest."
        )

    client = create_client(url, key)

    rows = [
        {
            "date": date,
            "rank": item.get("rank"),
            "title": item.get("title"),
            "url": item.get("url"),
            "summary": item.get("summary"),
            "why_it_matters": item.get("why_it_matters"),
            "score": float(item["score"]) if item.get("score") is not None else None,
            "source": item.get("source"),
        }
        for item in items
    ]

    try:
        client.table("digest_items").upsert(rows, on_conflict="date,rank").execute()
        logger.info("Saved %d digest items to Supabase for %s.", len(rows), date)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to upsert digest items to Supabase for {date}: {exc}"
        ) from exc
