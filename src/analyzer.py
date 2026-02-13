"""
Analyzer: read raw items from RawStore, call LLM for opportunities/directions/innovations,
write results to InsightStore. Skips raw items that already have an insight.
"""
import json
import logging
import os
from typing import Any

from openai import OpenAI
from dotenv import load_dotenv

from src.storage import RawStore, InsightStore

load_dotenv()
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert analyst. For each AI-related paper or news item, extract:
1. **商业机会 (opportunities)**: 1-3 short phrases on productization, ToB/ToC, or industry applications.
2. **技术方向 (directions)**: 1-3 short phrases on new methods, architectures, benchmarks, or datasets.
3. **创新点 (innovations)**: 1-3 short phrases on breakthroughs or reusable ideas vs existing work.

Respond ONLY with a single JSON object of the form:
{"opportunities": ["...", "..."], "directions": ["...", "..."], "innovations": ["...", "..."]}
Use empty lists if nothing relevant. Keep each string concise (under 80 chars)."""


def _parse_llm_response(text: str) -> dict[str, list[str]]:
    """Extract JSON from model response (may be wrapped in markdown)."""
    text = text.strip()
    # Strip markdown code block if present
    if "```" in text:
        parts = text.split("```")
        for p in parts:
            if "{" in p and "opportunities" in p:
                text = p.strip()
                break
    start = text.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"opportunities": [], "directions": [], "innovations": []}


def analyze_one(
    client: OpenAI,
    model: str,
    title: str,
    url: str,
    summary: str,
    summary_max_chars: int = 500,
) -> tuple[list[str], list[str], list[str]]:
    """Call LLM for one raw item; return (opportunities, directions, innovations)."""
    summary_trim = (summary or "")[:summary_max_chars]
    user = f"Title: {title}\nURL: {url}\nAbstract/Summary: {summary_trim}"
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
    )
    content = (resp.choices[0].message.content or "").strip()
    out = _parse_llm_response(content)
    return (
        out.get("opportunities") or [],
        out.get("directions") or [],
        out.get("innovations") or [],
    )


def run_analyze(
    raw_store: RawStore,
    insight_store: InsightStore,
    model: str | None = None,
    max_items_per_run: int = 30,
    summary_max_chars: int = 500,
    api_key: str | None = None,
    base_url: str | None = None,
) -> int:
    """
    Load raw items not yet analyzed, call LLM for each, write to InsightStore.
    Returns count of new insights written.
    """
    model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set; analyzer will not run")
        return 0
    client = OpenAI(api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL") or base_url)
    analyzed_ids = insight_store.get_analyzed_raw_item_ids()
    raw_items = raw_store.list_since(limit=max_items_per_run * 2)
    to_process = [r for r in raw_items if r.id is not None and r.id not in analyzed_ids][:max_items_per_run]
    count = 0
    for item in to_process:
        try:
            opps, dirs, inns = analyze_one(
                client, model, item.title, item.url, item.summary, summary_max_chars
            )
            insight_store.insert(item.id, opps, dirs, inns)
            count += 1
            logger.info("Analyzed raw_item_id=%s", item.id)
        except Exception as e:
            logger.exception("Analyzer failed for raw_item_id=%s: %s", item.id, e)
    return count
