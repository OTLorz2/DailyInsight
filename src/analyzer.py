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

SYSTEM_PROMPT = """你是一名专业分析师。请根据每条信息的类型采用自适应的分析流程，根据内容自行组织输出结构。

## 分析流程示例

**若为学术论文：**
1. 先简要总结论文内容与核心贡献；
2. 描述论文创新点（方法、实验或理论上的突破）；
3. 分析可能的改进策略或技术演进方向；
4. 分析商业落地可能性以及可行的商业计划或应用场景。
用你认为合适的中文键名组织成 JSON（如：总结、创新点、改进方向、商业计划 等）。

**若为新闻或资讯：**
1. 先总结新闻要点；
2. 突出值得关注的重点（政策、产品、融资、人事等）；
3. 描述潜在重要信息（如市场预测、行业动向、大众舆情、竞争格局等）。
用你认为合适的中文键名组织成 JSON（如：总结、重点、市场预测 等）。

**若为其他类型（博客、报告、产品发布等）：**
先总结内容，再分析关键信息与潜在影响，用合适的中文键名组织成 JSON。

## 输出要求

请仅回复一个 JSON 对象，键名使用中文，键和结构由你根据分析内容自行决定。值可以是字符串、字符串数组或嵌套对象。每条描述保持简洁（建议 80 字符以内）。"""


def _parse_llm_response(text: str) -> dict[str, Any]:
    """Extract JSON from model response (may be wrapped in markdown). Returns dict with arbitrary structure."""
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        for p in parts:
            if "{" in p:
                text = p.strip()
                if text.startswith("json"):
                    text = text[4:].strip()
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
        return {}


def analyze_one(
    client: OpenAI,
    model: str,
    title: str,
    url: str,
    summary: str,
    summary_max_chars: int = 500,
) -> dict[str, Any]:
    """Call LLM for one raw item; return analysis as a dict (structure determined by model)."""
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
    return _parse_llm_response(content)


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
            data = analyze_one(
                client, model, item.title, item.url, item.summary, summary_max_chars
            )
            insight_store.insert(item.id, data)
            count += 1
            logger.info("Analyzed raw_item_id=%s", item.id)
        except Exception as e:
            logger.exception("Analyzer failed for raw_item_id=%s: %s", item.id, e)
    return count
