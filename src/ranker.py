"""
ranker.py — Uses an LLM (Gemini via LangChain) to rank and summarize news items.
Returns the top 7 most significant AI stories.
"""

import json
import logging
import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM setup (Gemini 1.5 Flash via Google AI)
# ---------------------------------------------------------------------------

def _get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.environ["GEMINI_API_KEY"],
        temperature=0.3,
    )


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_SYSTEM_MESSAGE = """\
You are a sharp AI research analyst. Your job is to identify the most genuinely \
significant AI stories from a list of raw news items and return them in a structured format.

Criteria for ranking:
- Technical novelty: new capabilities, architectures, or findings not seen before
- Real-world impact: affects how developers, businesses, or society use AI
- Engagement potential: provocative, surprising, or shifts conventional thinking
- Avoid: pure hype, incremental updates, rehashed takes, vague opinion pieces

Return ONLY valid JSON. No preamble, no explanation, no markdown fences.\
"""

_HUMAN_TEMPLATE = """\
{numbered_items}

From the above, select the top 7 items. For each return:
- rank (1-7)
- title
- source
- url
- score (float 1-10, your novelty+impact rating)
- summary (2 clean sentences, no jargon padding)
- why_it_matters (2-3 sentences: what this changes, why a smart professional should care)

Return as a JSON array of 7 objects with exactly these keys.\
"""

_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_MESSAGE),
        ("human", _HUMAN_TEMPLATE),
    ]
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_numbered_block(items: list[dict]) -> str:
    """Format items as a numbered plaintext block for the prompt."""
    lines = []
    for idx, item in enumerate(items, start=1):
        title = item.get("title", "").strip()
        source = item.get("source", "").strip()
        summary = item.get("summary", "").strip()
        lines.append(f"{idx}. [{source}] {title}")
        if summary:
            lines.append(f"   {summary}")
        lines.append("")
    return "\n".join(lines)


def _merge_original_fields(ranked_items: list[dict], original_items: list[dict]) -> list[dict]:
    """
    Always override url and published on ranked items with values from the
    original fetched data. The LLM frequently returns wrong or hallucinated
    URLs, so we never trust its url field.
    """
    title_to_item = {item["title"].strip().lower(): item for item in original_items}
    for ranked in ranked_items:
        key = ranked.get("title", "").strip().lower()
        original = title_to_item.get(key)
        if original:
            ranked["url"] = original.get("url", ranked.get("url", "#"))
            ranked["published"] = original.get("published")
        else:
            # Fallback: keep LLM url if no title match found
            ranked.setdefault("url", "#")
            ranked.setdefault("published", None)
    return ranked_items


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def rank_and_summarize(items: list[dict]) -> list[dict]:
    """
    Use the LLM to select and rank the top 7 most significant AI stories.

    Args:
        items: List of raw news item dicts (title, summary, url, source, published).

    Returns:
        List of 7 dicts with keys: rank, title, source, url, score, summary, why_it_matters.

    Raises:
        ValueError: If the LLM returns invalid JSON or fewer than 7 items.
    """
    if not items:
        raise ValueError("No items provided to rank_and_summarize().")

    llm = _get_llm()
    chain = _PROMPT | llm

    numbered_block = _build_numbered_block(items)
    logger.info("Sending %d items to LLM for ranking…", len(items))

    response = chain.invoke({"numbered_items": numbered_block})
    raw_text = response.content.strip()

    # Strip accidental markdown fences if the model adds them despite instructions
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```[a-z]*\n?", "", raw_text)
        raw_text = re.sub(r"\n?```$", "", raw_text)

    try:
        ranked = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.error("LLM returned invalid JSON:\n%s", raw_text)
        raise ValueError(
            f"LLM response could not be parsed as JSON. JSONDecodeError: {exc}"
        ) from exc

    if not isinstance(ranked, list) or len(ranked) < 7:
        logger.error("LLM returned unexpected structure:\n%s", raw_text)
        raise ValueError(
            f"Expected a JSON array of 7 items, got {type(ranked).__name__} "
            f"with {len(ranked) if isinstance(ranked, list) else '?'} elements."
        )

    # Always patch url and published from original fetched data
    ranked = _merge_original_fields(ranked, items)

    logger.info(
        "Top 7 ranked stories:\n%s",
        "\n".join(
            f"  #{r.get('rank', '?')} (score {r.get('score', '?')}) {r.get('title', '')}"
            for r in ranked[:7]
        ),
    )

    return ranked[:7]


# Lazy import for the regex used inside rank_and_summarize
import re  # noqa: E402 — placed after function definition intentionally
