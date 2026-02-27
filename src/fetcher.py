"""
Fetcher: orchestrates source adapters, deduplicates, writes to RawStore.
Supports multiple sources: arxiv, biorxiv, medrxiv, semantic_scholar.
"""
import logging
from typing import Any

from src.storage import RawStore
from src.sources.arxiv import fetch_arxiv
from src.sources.biorxiv import fetch_biorxiv
from src.sources.medrxiv import fetch_medrxiv
from src.sources.semantic_scholar import fetch_semantic_scholar

logger = logging.getLogger(__name__)


def run_fetch(
    raw_store: RawStore,
    sources_config: dict[str, Any] | None = None,
) -> dict[str, int]:
    """
    Run all enabled source adapters, insert into RawStore (dedup by source+url).
    sources_config: e.g. {
        "arxiv": {"enabled": true, "categories": ["cs.AI"], "max_results": 50},
        "biorxiv": {"enabled": true, "max_results": 30},
        "medrxiv": {"enabled": false},
        "semantic_scholar": {"enabled": true, "max_results": 20, "categories": ["Computer Science"]}
    }
    Returns dict of source -> count of newly inserted items.
    """
    if sources_config is None:
        sources_config = {}
    counts: dict[str, int] = {}

    # arXiv
    arxiv_cfg = sources_config.get("arxiv") or {}
    if arxiv_cfg.get("enabled", True):
        categories = arxiv_cfg.get("categories")
        if not categories:
            raise ValueError(
                "arxiv.categories must be configured and non-empty. "
                "Example: ['cs.AI', 'cs.LG', 'cs.CL'] for AI papers, "
                "or ['physics.quant-ph'] for quantum physics papers."
            )
        max_results = arxiv_cfg.get("max_results", 50)
        try:
            items = fetch_arxiv(categories=categories, max_results=max_results)
            n = raw_store.insert_many(items, source="arxiv")
            counts["arxiv"] = n
            logger.info("Fetcher: arxiv inserted %d new items", n)
        except Exception as e:
            logger.exception("Fetcher: arxiv failed: %s", e)
            counts["arxiv"] = 0
    else:
        logger.info("Fetcher: arxiv is disabled")
        counts["arxiv"] = 0

    # bioRxiv
    biorxiv_cfg = sources_config.get("biorxiv") or {}
    if biorxiv_cfg.get("enabled", False):
        categories = biorxiv_cfg.get("categories")
        max_results = biorxiv_cfg.get("max_results", 30)
        try:
            items = fetch_biorxiv(categories=categories, max_results=max_results)
            n = raw_store.insert_many(items, source="biorxiv")
            counts["biorxiv"] = n
            logger.info("Fetcher: biorxiv inserted %d new items", n)
        except Exception as e:
            logger.exception("Fetcher: biorxiv failed: %s", e)
            counts["biorxiv"] = 0
    else:
        logger.debug("Fetcher: biorxiv is disabled")
        counts["biorxiv"] = 0

    # medRxiv
    medrxiv_cfg = sources_config.get("medrxiv") or {}
    if medrxiv_cfg.get("enabled", False):
        categories = medrxiv_cfg.get("categories")
        max_results = medrxiv_cfg.get("max_results", 30)
        try:
            items = fetch_medrxiv(categories=categories, max_results=max_results)
            n = raw_store.insert_many(items, source="medrxiv")
            counts["medrxiv"] = n
            logger.info("Fetcher: medrxiv inserted %d new items", n)
        except Exception as e:
            logger.exception("Fetcher: medrxiv failed: %s", e)
            counts["medrxiv"] = 0
    else:
        logger.debug("Fetcher: medrxiv is disabled")
        counts["medrxiv"] = 0

    # Semantic Scholar
    semantic_scholar_cfg = sources_config.get("semantic_scholar") or {}
    if semantic_scholar_cfg.get("enabled", False):
        categories = semantic_scholar_cfg.get("categories")
        max_results = semantic_scholar_cfg.get("max_results", 20)
        query = semantic_scholar_cfg.get("query")
        try:
            items = fetch_semantic_scholar(
                categories=categories, 
                max_results=max_results,
                query=query
            )
            n = raw_store.insert_many(items, source="semantic_scholar")
            counts["semantic_scholar"] = n
            logger.info("Fetcher: semantic_scholar inserted %d new items", n)
        except Exception as e:
            logger.exception("Fetcher: semantic_scholar failed: %s", e)
            counts["semantic_scholar"] = 0
    else:
        logger.debug("Fetcher: semantic_scholar is disabled")
        counts["semantic_scholar"] = 0

    return counts
