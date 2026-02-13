"""Verify RawStore and InsightStore: init, write, read."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.storage import RawStore, InsightStore, RawItem, Insight


def test_raw_store():
    path = os.path.join(os.path.dirname(__file__), "..", "data", "_test_raw.db")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        store = RawStore(path)
        id1 = store.insert("Title A", "https://a.org/1", "Summary A", "arxiv")
        assert id1 is not None
        id2 = store.insert("Title A", "https://a.org/1", "Summary A", "arxiv")
        assert id2 is None  # duplicate
        id3 = store.insert("Title B", "https://b.org/2", "Summary B", "arxiv")
        assert id3 is not None
        row = store.get_by_id(id1)
        assert row is not None and row.title == "Title A" and row.source == "arxiv"
        rows = store.list_since(limit=10)
        assert len(rows) >= 2
    finally:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass  # Windows may hold file handle


def test_insight_store():
    path = os.path.join(os.path.dirname(__file__), "..", "data", "_test_insight.db")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        store = InsightStore(path)
        pk = store.insert(1, ["opp1"], ["dir1"], ["inn1"])
        assert pk is not None
        row = store.get_by_id(pk)
        assert row is not None and row.raw_item_id == 1 and row.opportunities == ["opp1"]
        rows = store.list_since(limit=10)
        assert len(rows) >= 1
    finally:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass  # Windows may hold file handle


if __name__ == "__main__":
    test_raw_store()
    print("RawStore OK")
    test_insight_store()
    print("InsightStore OK")
