"""
Fetcher: orchestrates source adapters, deduplicates, writes to RawStore.
Current implementation: arXiv only.
"""
import logging
from typing import Any

from src.storage import RawStore
from src.sources.arxiv import fetch_arxiv

logger = logging.getLogger(__name__)


def run_fetch(
    raw_store: RawStore,
    sources_config: dict[str, Any] | None = None,
) -> dict[str, int]:
    """
    Run all enabled source adapters, insert into RawStore (dedup by source+url).
    sources_config: e.g. {"arxiv": {"enabled": true, "categories": ["cs.AI"], "max_results": 50}}.
    Returns dict of source -> count of newly inserted items.
    """
    if sources_config is None:
        sources_config = {}
    counts: dict[str, int] = {}

    # arXiv
    arxiv_cfg = sources_config.get("arxiv") or {}
    if arxiv_cfg.get("enabled", True):
        categories = arxiv_cfg.get("categories") or ["cs.AI", "cs.LG", "cs.CL"]
        max_results = arxiv_cfg.get("max_results", 50)
        try:
            items = fetch_arxiv(categories=categories, max_results=max_results)
            n = raw_store.insert_many(items, source="arxiv")
            counts["arxiv"] = n
            logger.info("Fetcher: arxiv inserted %d new items", n)
        except Exception as e:
            logger.exception("Fetcher: arxiv failed: %s", e)
            counts["arxiv"] = 0

    return counts
