"""Verify Fetcher: orchestrates arXiv adapter, dedup, writes to RawStore."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch
from src.storage import RawStore
from src.fetcher import run_fetch


@patch("src.fetcher.fetch_arxiv")
def test_fetcher_arxiv_to_raw_store(mock_fetch):
    mock_fetch.return_value = [
        {"title": "Paper One", "url": "http://arxiv.org/abs/2401.00001", "summary": "Abstract 1"},
        {"title": "Paper Two", "url": "http://arxiv.org/abs/2401.00002", "summary": "Abstract 2"},
    ]
    path = os.path.join(os.path.dirname(__file__), "..", "data", "_test_fetcher.db")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        store = RawStore(path)
        counts = run_fetch(store, sources_config={"arxiv": {"enabled": True, "max_results": 10}})
        assert counts.get("arxiv") == 2
        rows = store.list_since(limit=10)
        assert len(rows) == 2
        # dedup: run again, no new inserts
        counts2 = run_fetch(store, sources_config={"arxiv": {"enabled": True}})
        assert counts2.get("arxiv") == 0
        rows2 = store.list_since(limit=10)
        assert len(rows2) == 2
    finally:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


if __name__ == "__main__":
    test_fetcher_arxiv_to_raw_store()
    print("Fetcher OK")
