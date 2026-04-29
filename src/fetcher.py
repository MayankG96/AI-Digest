"""
fetcher.py — Fetches AI news from Hacker News, ArXiv, and RSS feeds.
Returns a deduplicated list of items published in the last 24 hours.
"""

import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

import feedparser
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _truncate(text: str, limit: int = 300) -> str:
    """Truncate text to `limit` characters."""
    if not text:
        return ""
    text = text.strip()
    return text[:limit] + "…" if len(text) > limit else text


def _strip_html(text: str) -> str:
    """Remove HTML tags from a string."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def _parse_dt(value) -> datetime:
    """Convert various date representations to an aware UTC datetime."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, time.struct_time):
        return datetime(*value[:6], tzinfo=timezone.utc)
    if isinstance(value, str):
        for fmt in (
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S GMT",
        ):
            try:
                dt = datetime.strptime(value.strip(), fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except ValueError:
                continue
    return datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# Source 1: Hacker News (Algolia API)
# ---------------------------------------------------------------------------

def _fetch_hacker_news(cutoff: datetime) -> list[dict]:
    """Fetch AI stories from Hacker News posted after `cutoff`."""
    unix_cutoff = int(cutoff.timestamp())
    url = (
        f"https://hn.algolia.com/api/v1/search"
        f"?query=AI&tags=story&numericFilters=created_at_i>{unix_cutoff}"
    )
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("Hacker News fetch failed: %s", exc)
        return []

    items = []
    for hit in data.get("hits", []):
        title = (hit.get("title") or "").strip()
        if not title:
            continue
        story_text = hit.get("story_text") or ""
        summary = _truncate(_strip_html(story_text), 300)
        url_val = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
        published = _parse_dt(hit.get("created_at_i") or hit.get("created_at", ""))
        items.append(
            {
                "title": title,
                "summary": summary,
                "url": url_val,
                "source": "Hacker News",
                "published": published,
            }
        )
    logger.info("Hacker News: fetched %d items", len(items))
    return items


# ---------------------------------------------------------------------------
# Source 2: ArXiv
# ---------------------------------------------------------------------------

_ARXIV_NS = "http://www.w3.org/2005/Atom"


def _fetch_arxiv() -> list[dict]:
    """Fetch recent AI/ML papers from ArXiv."""
    url = (
        "http://export.arxiv.org/api/query"
        "?search_query=cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CL"
        "&sortBy=submittedDate&sortOrder=descending&max_results=30"
    )
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
    except Exception as exc:
        logger.warning("ArXiv fetch failed: %s", exc)
        return []

    ns = {"atom": _ARXIV_NS}
    items = []
    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        title = (title_el.text or "").strip().replace("\n", " ") if title_el is not None else ""
        if not title:
            continue

        summary_el = entry.find("atom:summary", ns)
        raw_summary = (summary_el.text or "").strip() if summary_el is not None else ""
        summary = _truncate(raw_summary, 300)

        link_el = entry.find("atom:link[@rel='alternate']", ns)
        if link_el is None:
            link_el = entry.find("atom:link", ns)
        url_val = link_el.attrib.get("href", "") if link_el is not None else ""

        pub_el = entry.find("atom:published", ns)
        pub_str = pub_el.text.strip() if pub_el is not None else ""
        published = _parse_dt(pub_str)

        items.append(
            {
                "title": title,
                "summary": summary,
                "url": url_val,
                "source": "ArXiv",
                "published": published,
            }
        )

    logger.info("ArXiv: fetched %d items", len(items))
    return items


# ---------------------------------------------------------------------------
# Source 3: RSS feeds
# ---------------------------------------------------------------------------

_RSS_FEEDS = [
    ("https://venturebeat.com/category/ai/feed/", "VentureBeat"),
    ("https://techcrunch.com/category/artificial-intelligence/feed/", "TechCrunch"),
    ("https://www.deeplearning.ai/the-batch/feed/", "The Batch"),
    ("https://jack-clark.net/feed/", "Import AI"),
]


def _fetch_rss_feed(feed_url: str, source_name: str) -> list[dict]:
    """Fetch and parse a single RSS feed."""
    try:
        parsed = feedparser.parse(feed_url)
        if parsed.get("bozo") and not parsed.get("entries"):
            raise ValueError(f"Feed parse error: {parsed.get('bozo_exception')}")
    except Exception as exc:
        logger.warning("%s RSS fetch failed: %s", source_name, exc)
        return []

    items = []
    for entry in parsed.get("entries", []):
        title = (entry.get("title") or "").strip()
        if not title:
            continue

        raw_summary = entry.get("summary") or entry.get("description") or ""
        summary = _truncate(_strip_html(raw_summary), 300)
        url_val = entry.get("link", "")

        pub_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        published = _parse_dt(pub_parsed) if pub_parsed else datetime.now(tz=timezone.utc)

        items.append(
            {
                "title": title,
                "summary": summary,
                "url": url_val,
                "source": source_name,
                "published": published,
            }
        )

    logger.info("%s: fetched %d items", source_name, len(items))
    return items


def _fetch_all_rss(cutoff: datetime) -> list[dict]:
    """Fetch all RSS feeds and filter to items published after cutoff."""
    items = []
    for feed_url, source_name in _RSS_FEEDS:
        feed_items = _fetch_rss_feed(feed_url, source_name)
        items.extend(feed_items)
    # Filter to 24-hour window
    return [i for i in items if i["published"] >= cutoff]


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return url


def _deduplicate(items: list[dict]) -> list[dict]:
    """Deduplicate by URL, then by (domain, title prefix)."""
    seen_urls: set[str] = set()
    seen_domain_title: set[str] = set()
    result = []

    for item in items:
        url = item.get("url", "")
        if url and url in seen_urls:
            continue

        domain = _domain(url)
        title_prefix = item.get("title", "")[:40].lower().strip()
        key = f"{domain}::{title_prefix}"
        if key in seen_domain_title:
            continue

        if url:
            seen_urls.add(url)
        seen_domain_title.add(key)
        result.append(item)

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_all_items() -> list[dict]:
    """
    Fetch AI news from all sources published in the last 24 hours.
    Returns up to 40 deduplicated items sorted by published date (newest first).
    """
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=24)

    all_items: list[dict] = []

    # Hacker News
    all_items.extend(_fetch_hacker_news(cutoff))

    # ArXiv (filter to 24h window)
    arxiv_items = _fetch_arxiv()
    all_items.extend([i for i in arxiv_items if i["published"] >= cutoff])

    # RSS feeds
    all_items.extend(_fetch_all_rss(cutoff))

    # Deduplicate
    unique_items = _deduplicate(all_items)

    # Sort by published descending and cap at 40
    unique_items.sort(key=lambda x: x["published"], reverse=True)
    final = unique_items[:40]

    logger.info("Total items after deduplication: %d", len(final))
    return final
